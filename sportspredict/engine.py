"""Leak-free feature construction, models and walk-forward evaluation.

Canonical match schema (one row per match, chronological):
    date, home, away, home_score, away_score
optional columns:
    neutral (0/1), friendly (0/1), surface (tennis), odds_home, odds_draw, odds_away,
    home_birth, away_birth (club founding date / player DOB, ISO yyyy-mm-dd)
For tennis "home"/"away" are just player 1 / player 2 (randomised so the winner
is never systematically in one column).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import esoteric


@dataclass
class SportConfig:
    name: str
    draws: bool            # 3-way outcome?
    elo_k: float
    elo_hfa: float         # Elo points
    mov: bool              # margin-of-victory Elo multiplier
    season_gap_days: int   # gap that triggers between-season regression
    season_regress: float  # fraction regressed to mean
    goal_model: bool       # Poisson attack/defence model (low-scoring sports)
    margin_lr: float       # learning rate for points-margin rating
    form_alpha: float      # EWMA weight of latest result


SPORTS = {
    "soccer": SportConfig("soccer", True, 20, 60, True, 60, 0.20, True, 0.0, 0.25),
    "hockey": SportConfig("hockey", False, 8, 35, True, 90, 0.30, True, 0.0, 0.15),
    "basketball": SportConfig("basketball", False, 20, 100, True, 90, 0.25, False, 0.04, 0.15),
    "tennis": SportConfig("tennis", False, 32, 0, False, 10_000, 0.0, False, 0.0, 0.20),
}


# ------------------------------------------------------------------ ratings
class Elo:
    def __init__(self, k, hfa, mov, mean=1500.0):
        self.k, self.hfa, self.mov, self.mean = k, hfa, mov, mean
        self.r = defaultdict(lambda: mean)

    def expect(self, h, a, neutral):
        d = self.r[h] - self.r[a] + (0 if neutral else self.hfa)
        return 1 / (1 + 10 ** (-d / 400)), d

    def update(self, h, a, neutral, sh, sa, k_mult=1.0):
        e, d = self.expect(h, a, neutral)
        res = 1.0 if sh > sa else (0.5 if sh == sa else 0.0)
        mult = 1.0
        if self.mov and sh != sa:
            win_d = d if sh > sa else -d
            mult = math.log(abs(sh - sa) + 1) * 2.2 / (win_d * 0.001 + 2.2)
        delta = self.k * k_mult * mult * (res - e)
        self.r[h] += delta
        self.r[a] -= delta

    def regress(self, team, frac):
        self.r[team] = self.r[team] * (1 - frac) + self.mean * frac


class GoalModel:
    """Online Poisson attack/defence model (exponentially weighted gradient steps)."""

    def __init__(self, lr=0.04):
        self.lr = lr
        self.att = defaultdict(float)
        self.dfn = defaultdict(float)
        self.mu = math.log(1.3)
        self.hfa = 0.2

    def rates(self, h, a, neutral):
        hfa = 0 if neutral else self.hfa
        lh = math.exp(self.mu + hfa + self.att[h] - self.dfn[a])
        la = math.exp(self.mu + self.att[a] - self.dfn[h])
        return lh, la

    def probs(self, h, a, neutral, max_goals=12):
        lh, la = self.rates(h, a, neutral)
        ph, pa = poisson.pmf(np.arange(max_goals), lh), poisson.pmf(np.arange(max_goals), la)
        m = np.outer(ph, pa)
        return float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum()), lh, la

    def update(self, h, a, neutral, gh, ga):
        lh, la = self.rates(h, a, neutral)
        gh, ga = min(gh, 8), min(ga, 8)
        eh, ea = gh - lh, ga - la
        self.att[h] += self.lr * eh
        self.dfn[a] -= self.lr * eh
        self.att[a] += self.lr * ea
        self.dfn[h] -= self.lr * ea
        self.mu += self.lr * 0.02 * (eh + ea)
        if not neutral:
            self.hfa += self.lr * 0.02 * (eh - ea)


class MarginRating:
    """Online points-margin rating: E[margin] = r_h - r_a + hfa."""

    def __init__(self, lr):
        self.lr, self.r, self.hfa = lr, defaultdict(float), 3.0

    def expect(self, h, a, neutral):
        return self.r[h] - self.r[a] + (0 if neutral else self.hfa)

    def update(self, h, a, neutral, sh, sa):
        err = max(-30, min(30, (sh - sa))) - self.expect(h, a, neutral)
        self.r[h] += self.lr * err
        self.r[a] -= self.lr * err
        if not neutral:
            self.hfa += self.lr * 0.01 * err


# ------------------------------------------------------------------ features
STAT_FEATURES = ["elo_diff", "elo_p", "form_diff", "gd_form_diff", "rest_diff",
                 "b2b_diff", "exp_min", "neutral", "friendly"]


def build_features(df: pd.DataFrame, sport: str, esoteric_on: bool = True,
                   fixtures: pd.DataFrame | None = None) -> pd.DataFrame:
    """Walk through matches chronologically, recording pre-match state, then update.

    If `fixtures` is given, ratings are built from all of `df` (played matches) and
    feature rows are returned for the fixtures instead.
    """
    cfg = SPORTS[sport]
    elo = Elo(cfg.elo_k, cfg.elo_hfa, cfg.mov)
    surf_elo = defaultdict(lambda: Elo(cfg.elo_k, 0, False))
    gm = GoalModel() if cfg.goal_model else None
    mr = MarginRating(cfg.margin_lr) if cfg.margin_lr else None
    form = defaultdict(lambda: 0.5)
    gdf = defaultdict(float)
    last = {}
    prev_last = {}
    n_games = defaultdict(int)
    tot = {}                                   # EWMA of total goals in a team's matches
    tot_for, tot_ag = {}, {}                   # EWMA goals scored / conceded
    lg_tot = defaultdict(lambda: 2.6)          # rolling competition scoring level
    lg_key = (lambda r: r.get("league", "all")) if "league" in df.columns else (lambda r: "all")

    def row_feats(r):
        h, a, d = r.home, r.away, r.date
        neutral = bool(r.get("neutral", 0) or 0)
        for t in (h, a):  # between-season regression to the mean
            if t in last and (d - last[t]).days > cfg.season_gap_days and cfg.season_regress:
                elo.regress(t, cfg.season_regress)
        p, ed = elo.expect(h, a, neutral)
        f = {"elo_diff": ed / 100, "elo_p": p,
             "form_diff": form[h] - form[a], "gd_form_diff": gdf[h] - gdf[a],
             "neutral": float(neutral), "friendly": float(r.get("friendly", 0) or 0),
             "exp_min": math.log1p(min(n_games[h], n_games[a]))}
        rest = [min((d - last[t]).days, 10) if t in last else 10 for t in (h, a)]
        f["rest_diff"] = (rest[0] - rest[1]) / 10
        f["b2b_diff"] = float(rest[0] <= 1) - float(rest[1] <= 1)
        if gm:
            ph, pd_, pa, lh, la = gm.probs(h, a, neutral)
            f.update({"gm_ph": ph, "gm_pd": pd_, "gm_pa": pa, "gm_xg_diff": lh - la, "gm_xg_sum": lh + la})
            # totals (over/under) inputs, prefixed ou_
            lg = lg_tot[lg_key(r)]
            f["ou_lg_tot"] = lg
            f["ou_tot_h"], f["ou_tot_a"] = tot.get(h, lg), tot.get(a, lg)
            f["ou_att_x_def"] = tot_for.get(h, lg / 2) + tot_ag.get(a, lg / 2) + tot_for.get(a, lg / 2) + tot_ag.get(h, lg / 2)
            f["ou_xg_h"], f["ou_xg_a"] = lh, la
            f["ou_xg_gap"] = abs(lh - la)          # mismatches tend to produce more goals
        if mr:
            f["margin_exp"] = mr.expect(h, a, neutral) / 10
        if sport == "tennis" and isinstance(r.get("surface"), str):
            se = surf_elo[r.surface]
            f["surface_elo_diff"] = (se.r[h] - se.r[a]) / 100
        if all(c in r and pd.notna(r[c]) for c in ("odds_home", "odds_away")):
            inv = [1 / r.odds_home, 1 / r.odds_away] + ([1 / r.odds_draw] if cfg.draws and pd.notna(r.get("odds_draw")) else [])
            s = sum(inv)
            f["mkt_ph"], f["mkt_pa"] = inv[0] / s, inv[1] / s
            if len(inv) == 3:
                f["mkt_pd"] = inv[2] / s
        if all(c in r and pd.notna(r[c]) for c in ("odds_over", "odds_under")):
            io, iu = 1 / r.odds_over, 1 / r.odds_under
            f["ou_mkt_p_over"] = io / (io + iu)
        if esoteric_on:
            hb = r.get("home_birth") if "home_birth" in r and pd.notna(r.get("home_birth")) else None
            ab = r.get("away_birth") if "away_birth" in r and pd.notna(r.get("away_birth")) else None
            f.update({"eso_" + k: v for k, v in esoteric.match_features(str(h), str(a), d, hb, ab).items()})
        return f, neutral

    out = []
    for r in df.itertuples(index=False):
        r = r._asdict()
        r = pd.Series(r)
        f, neutral = row_feats(r)
        if fixtures is None:
            f["_idx"] = len(out)
            out.append(f)
        h, a, sh, sa, d = r.home, r.away, r.home_score, r.away_score, r.date
        elo.update(h, a, neutral, sh, sa, k_mult=0.6 if f["friendly"] else 1.0)
        if sport == "tennis" and isinstance(r.get("surface"), str):
            surf_elo[r.surface].update(h, a, True, sh, sa)
        if gm:
            gm.update(h, a, neutral, sh, sa)
            t, w = min(sh + sa, 10), 0.12
            for team, gf, ga in ((h, sh, sa), (a, sa, sh)):
                lg = lg_tot[lg_key(r)]
                tot[team] = (1 - w) * tot.get(team, lg) + w * t
                tot_for[team] = (1 - w) * tot_for.get(team, lg / 2) + w * min(gf, 8)
                tot_ag[team] = (1 - w) * tot_ag.get(team, lg / 2) + w * min(ga, 8)
            lg_tot[lg_key(r)] = 0.995 * lg_tot[lg_key(r)] + 0.005 * t
        if mr:
            mr.update(h, a, neutral, sh, sa)
        res = 1.0 if sh > sa else (0.5 if sh == sa else 0.0)
        a_ = cfg.form_alpha
        form[h] = (1 - a_) * form[h] + a_ * res
        form[a] = (1 - a_) * form[a] + a_ * (1 - res)
        g = max(-5, min(5, sh - sa)) if sport != "basketball" else max(-30, min(30, sh - sa)) / 6
        gdf[h] = (1 - a_) * gdf[h] + a_ * g
        gdf[a] = (1 - a_) * gdf[a] - a_ * g
        n_games[h] += 1
        n_games[a] += 1
        last[h] = last[a] = d

    if fixtures is not None:
        rows = [row_feats(pd.Series(r._asdict()))[0] for r in fixtures.itertuples(index=False)]
        return pd.DataFrame(rows)
    return pd.DataFrame(out)


def outcome(df: pd.DataFrame, sport: str) -> np.ndarray:
    """0 = home/player1 win, 1 = draw, 2 = away/player2 win (2-way sports: 0/2)."""
    y = np.where(df.home_score > df.away_score, 0, np.where(df.home_score < df.away_score, 2, 1))
    if not SPORTS[sport].draws:
        y = np.where(y == 1, 0, y)  # should not happen once OT/SO is counted
    return y


# ------------------------------------------------------------------ model
def make_model(C=0.5):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))


def feature_sets(cols):
    stat = [c for c in cols if not c.startswith(("eso_", "ou_"))]
    eso = [c for c in cols if c.startswith("eso_") and not c.startswith("eso_sum_")]
    return {"stat": stat, "stat+eso": stat + eso, "eso_only": eso + ["neutral"]}


def walk_forward(X: pd.DataFrame, y: np.ndarray, dates: pd.Series, cols, start_year: int,
                 min_train: int = 1000, C=0.5):
    """Retrain once per calendar year on all prior matches; predict that year."""
    years = dates.dt.year.values
    classes = np.unique(y)
    P = np.full((len(y), len(classes)), np.nan)
    for yr in sorted(set(years[years >= start_year])):
        tr, te = years < yr, years == yr
        if tr.sum() < min_train:
            continue
        m = make_model(C).fit(X.loc[tr, cols].values, y[tr])
        p = m.predict_proba(X.loc[te, cols].values)
        full = np.zeros((te.sum(), len(classes)))
        for j, c in enumerate(m.classes_):
            full[:, np.searchsorted(classes, c)] = p[:, j]
        P[te] = full
    return P, classes


def metrics(P, y, classes):
    ok = ~np.isnan(P[:, 0])
    P, y = P[ok], y[ok]
    yi = np.searchsorted(classes, y)
    pred = P.argmax(1)
    onehot = np.eye(len(classes))[yi]
    return {"n": int(ok.sum()), "accuracy": float((pred == yi).mean()),
            "log_loss": float(-np.log(np.clip(P[np.arange(len(yi)), yi], 1e-12, 1)).mean()),
            "brier": float(((P - onehot) ** 2).sum(1).mean())}


def per_match_logloss(P, y, classes):
    yi = np.searchsorted(classes, y)
    return -np.log(np.clip(P[np.arange(len(yi)), yi], 1e-12, 1))


def selective_accuracy(P, y, classes, dates, target=0.70):
    """Honest 'confidence filter': for each year, pick the lowest confidence
    threshold that reached `target` accuracy on all *previous* out-of-sample
    years, then apply it to the current year. Returns realised accuracy/coverage."""
    ok = ~np.isnan(P[:, 0])
    conf, hit = P.max(1), (P.argmax(1) == np.searchsorted(classes, y))
    years = dates.dt.year.values
    picked, total = [], 0
    for yr in sorted(set(years[ok])):
        past, cur = ok & (years < yr), ok & (years == yr)
        total += cur.sum()
        if past.sum() < 500:
            continue
        thr = None
        for t in np.arange(0.40, 0.96, 0.01):
            sel = past & (conf >= t)
            if sel.sum() >= 100 and hit[sel].mean() >= target:
                thr = t
                break
        if thr is None:
            continue
        picked.append((cur & (conf >= thr)))
    if not picked:
        return {"accuracy": float("nan"), "coverage": 0.0, "n_selected": 0}
    sel = np.any(picked, axis=0)
    eval_n = sum(1 for _ in picked)
    return {"accuracy": float(hit[sel].mean()) if sel.sum() else float("nan"),
            "coverage": float(sel.sum() / ok.sum()), "n_selected": int(sel.sum())}


def coverage_curve(P, y, classes, qs=(1.0, 0.75, 0.5, 0.3, 0.2, 0.1)):
    ok = ~np.isnan(P[:, 0])
    P, y = P[ok], y[ok]
    conf, hit = P.max(1), (P.argmax(1) == np.searchsorted(classes, y))
    order = np.argsort(-conf)
    return {q: float(hit[order[: max(1, int(q * len(order)))]].mean()) for q in qs}


def bootstrap_diff(a, b, n=2000, seed=0):
    """95% CI of mean(a-b) by paired bootstrap."""
    rng = np.random.default_rng(seed)
    d = a - b
    means = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(n)]
    return float(d.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ------------------------------------------------------------------ totals (over/under)
def totals_target(df, line=2.5):
    return ((df.home_score + df.away_score) > line).astype(int).values


def add_totals_features(X: pd.DataFrame, line=2.5) -> pd.DataFrame:
    """Poisson P(total > line) from the goal model's expected goals, plus logit."""
    X = X.copy()
    if "gm_xg_sum" in X:
        p = 1 - poisson.cdf(math.floor(line), X.gm_xg_sum.clip(lower=0.05))
        X["ou_poisson_p_over"] = p
        X["ou_poisson_logit"] = np.log(np.clip(p, 1e-4, 1 - 1e-4) / np.clip(1 - p, 1e-4, 1))
    return X


def totals_feature_sets(cols):
    stat = [c for c in cols if c.startswith("ou_")] + [c for c in ("gm_xg_sum", "gm_pd", "friendly", "neutral", "exp_min") if c in cols]
    eso = [c for c in cols if c.startswith("eso_") and not c.startswith("eso_diff_")]
    return {"stat": stat, "stat+eso": stat + eso, "eso_only": eso + ["neutral"]}
