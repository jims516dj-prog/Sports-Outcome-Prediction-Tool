"""Goal markets for football: over/under 2.5 goals and both teams to score (BTTS).

Two views, kept separate and compared on the same matches:
  * statistics - each team's recent scoring/conceding form and an online Poisson
    attack/defence model, built in kickoff order from the matches in the dataset
  * astrology  - what the engines imply: the synthesised "most likely" scoreline,
    Chokoisky's goal difference, Frawley's goal counts, high/low-scoring observations

Training (run with every ML retrain) fits logistic-regression models on the older 75% of
finished matches and scores them on the newest 25% they never saw: statistics only,
statistics + astrology, astrology only, plus simple baselines. The variant with the best
held-out log-loss is refitted on all finished matches and used for upcoming predictions.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone

import joblib
import numpy as np
from scipy.stats import poisson
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODEL_DIR = os.environ.get("ML_MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))
LATEST = os.path.join(MODEL_DIR, "goals_latest.joblib")
MARKETS = {"over25": "Over 2.5 goals", "btts": "Both teams to score"}
STAT_COLS = ["xg_h", "xg_a", "xg_sum", "p_over_poisson", "p_btts_poisson", "gf_h", "ga_h", "gf_a", "ga_a",
             "over_rate_h", "over_rate_a", "btts_rate_h", "btts_rate_a", "lg_goals", "mismatch", "exp_min"]
ASTRO_COLS = ["astro_likely_total", "astro_likely_btts", "astro_abs_chok", "astro_chok_gd", "astro_fraw_w",
              "astro_fraw_l", "astro_fraw_n", "astro_fraw_late", "astro_high", "astro_low", "astro_sky",
              "astro_d9", "astro_sandhi", "astro_agree", "astro_abs_rao"]
MIN_TRAIN = 300


# ------------------------------------------------------------------ data
def load(conn):
    rows = conn.execute("""
        SELECT m.id, m."kickoffGMT", m."teamAId", m."teamBId", coalesce(m.league, 'other'), m."scoreA", m."scoreB",
               m.status, m."oddsA", m."oddsB", m."mlFeatures",
               m.synthesis->'goal_range'->>'likely', m.synthesis->'observations',
               m."verdictFrawley"->'goals', m."verdictFrawley"->>'n_testimonies', m."verdictFrawley"->>'late_goal',
               m."verdictChokoisky"->>'total', m."verdictChokoisky"->>'goal_diff', m."verdictRao"->>'diff',
               m.synthesis->>'agreement', m.sport
        FROM "Match" m
        WHERE NOT m.deleted AND m.status IN ('completed', 'pending') AND m.sport = 'football'
        ORDER BY m."kickoffGMT", m.id""").fetchall()
    out = []
    for r in rows:
        (mid, ko, ta, tb, lg, sa, sb, status, oa, ob, feats, likely, obs, fgoals, fn, flate, ctot, cgd, rdiff,
         agree, _sport) = r
        out.append({"id": mid, "ko": ko, "home": ta, "away": tb, "league": lg, "sa": sa, "sb": sb,
                    "finished": status == "completed" and sa is not None and sb is not None,
                    "pending": status == "pending", "odds_a": oa, "odds_b": ob,
                    "feats": feats if isinstance(feats, dict) else (json.loads(feats) if feats else {}),
                    "likely": likely, "obs": obs if isinstance(obs, list) else (json.loads(obs) if obs else []),
                    "fgoals": fgoals if isinstance(fgoals, dict) else (json.loads(fgoals) if fgoals else None),
                    "fn": float(fn or 0), "flate": flate == "true", "ctot": float(ctot or 0), "cgd": float(cgd or 0),
                    "rdiff": float(rdiff or 0), "agree": float(agree or 0)})
    return out


def parse_likely(s):
    """Synthesis 'most likely' score, written Team A–Team B (en dash)."""
    if not s:
        return None
    for sep in ("–", "-"):
        if sep in s:
            try:
                a, b = s.split(sep)
                return int(a), int(b)
            except ValueError:
                return None
    return None


def build_features(rows):
    """Pre-match features in kickoff order; ratings update only after each finished match."""
    a_ = 0.12
    gf, ga, over, btts = defaultdict(lambda: None), defaultdict(lambda: None), defaultdict(lambda: None), defaultdict(lambda: None)
    n = defaultdict(int)
    att, dfn = defaultdict(float), defaultdict(float)
    mu, hfa, lr = math.log(1.35), 0.2, 0.04
    lg_goals = defaultdict(lambda: 2.7)
    X = []
    for r in rows:
        h, a, lg = r["home"], r["away"], r["league"]
        L = lg_goals[lg]
        lh = math.exp(mu + hfa + att[h] - dfn[a])
        la = math.exp(mu + att[a] - dfn[h])
        p_over = 1 - poisson.cdf(2, lh + la)
        p_btts = (1 - math.exp(-lh)) * (1 - math.exp(-la))
        val = lambda d, t, dflt: d[t] if d[t] is not None else dflt
        mismatch = 0.0
        if r["odds_a"] and r["odds_b"]:
            mismatch = abs(1 / r["odds_a"] - 1 / r["odds_b"])
        f = {"xg_h": lh, "xg_a": la, "xg_sum": lh + la, "p_over_poisson": p_over, "p_btts_poisson": p_btts,
             "gf_h": val(gf, h, L / 2), "ga_h": val(ga, h, L / 2), "gf_a": val(gf, a, L / 2), "ga_a": val(ga, a, L / 2),
             "over_rate_h": val(over, h, 0.5), "over_rate_a": val(over, a, 0.5),
             "btts_rate_h": val(btts, h, 0.5), "btts_rate_a": val(btts, a, 0.5),
             "lg_goals": L, "mismatch": mismatch, "exp_min": math.log1p(min(n[h], n[a]))}
        lk = parse_likely(r["likely"])
        fg = r["fgoals"] or {}
        obs = " ".join(r["obs"] or [])
        feats = r["feats"] or {}
        f.update({"astro_likely_total": (lk[0] + lk[1]) if lk else 2.0,
                  "astro_likely_btts": float(bool(lk and lk[0] > 0 and lk[1] > 0)),
                  "astro_abs_chok": abs(r["ctot"]), "astro_chok_gd": r["cgd"],
                  "astro_fraw_w": float(fg.get("winner", 0) or 0), "astro_fraw_l": float(fg.get("loser", 0) or 0),
                  "astro_fraw_n": r["fn"], "astro_fraw_late": float(r["flate"]),
                  "astro_high": float("high-scoring" in obs), "astro_low": float("low-scoring" in obs),
                  "astro_sky": float(bool(feats.get("chokoisky_sky_present"))),
                  "astro_d9": float(bool(feats.get("chokoisky_d9_cusp_strong_planet_present"))),
                  "astro_sandhi": float(bool(feats.get("sandhi_window_active"))),
                  "astro_agree": r["agree"], "astro_abs_rao": abs(r["rdiff"])})
        f["astro_rule_over"] = float(lk is not None and lk[0] + lk[1] >= 3)
        f["astro_rule_btts"] = f["astro_likely_btts"]
        X.append(f)
        if r["finished"]:
            sh, sa = int(r["sa"]), int(r["sb"])
            for t, scored, conceded in ((h, sh, sa), (a, sa, sh)):
                gf[t] = (1 - a_) * val(gf, t, L / 2) + a_ * min(scored, 6)
                ga[t] = (1 - a_) * val(ga, t, L / 2) + a_ * min(conceded, 6)
                over[t] = (1 - a_) * val(over, t, 0.5) + a_ * float(sh + sa >= 3)
                btts[t] = (1 - a_) * val(btts, t, 0.5) + a_ * float(sh > 0 and sa > 0)
                n[t] += 1
            eh, ea = min(sh, 8) - lh, min(sa, 8) - la
            att[h] += lr * eh
            dfn[a] -= lr * eh
            att[a] += lr * ea
            dfn[h] -= lr * ea
            mu += lr * 0.02 * (eh + ea)
            hfa += lr * 0.02 * (eh - ea)
            lg_goals[lg] = 0.99 * L + 0.01 * min(sh + sa, 10)
    return X


def targets(rows):
    y_over = np.array([float(r["sa"] + r["sb"] >= 3) if r["finished"] else np.nan for r in rows])
    y_btts = np.array([float(r["sa"] > 0 and r["sb"] > 0) if r["finished"] else np.nan for r in rows])
    return {"over25": y_over, "btts": y_btts}


def _mat(X, cols, idx):
    return np.array([[X[i][c] for c in cols] for i in idx], dtype=float)


def _model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=2000))


def _logloss(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def _threshold(p, y, target=0.65, min_n=100):
    """Lowest confidence at which held-out picks were right >= target (for a 'strong pick' flag)."""
    conf, hit = np.maximum(p, 1 - p), ((p >= 0.5) == (y == 1))
    for t in np.arange(0.5, 0.91, 0.01):
        sel = conf >= t
        if sel.sum() >= min_n and hit[sel].mean() >= target:
            return {"threshold": round(float(t), 2), "accuracy": float(hit[sel].mean()), "coverage": float(sel.mean())}
    return None


# ------------------------------------------------------------------ training
def train(conn, version: int | None = None) -> dict:
    rows = load(conn)
    X = build_features(rows)
    Y = targets(rows)
    fin = [i for i, r in enumerate(rows) if r["finished"]]
    res = {"n_finished": len(fin), "trained_at": datetime.now(timezone.utc).isoformat(), "markets": {}}
    if len(fin) < MIN_TRAIN:
        res["cold_start"] = True
        res["message"] = f"{len(fin)} finished football matches; {MIN_TRAIN} needed to train the goal models. Predictions use the Poisson model alone until then."
        _save({"version": version, "models": {}, "metrics": res})
        predict_pending(conn)
        return res
    cut = int(len(fin) * 0.75)
    tr, te = fin[:cut], fin[cut:]
    models = {}
    for mk, y in Y.items():
        ytr, yte = y[tr], y[te]
        m = {"label": MARKETS[mk], "n_train": len(tr), "n_test": len(te), "base_rate": float(yte.mean()),
             "methods": {}}
        m["methods"]["always_more_common"] = {"accuracy": float(max(yte.mean(), 1 - yte.mean())), "log_loss": None}
        pcol = "p_over_poisson" if mk == "over25" else "p_btts_poisson"
        pp = np.array([X[i][pcol] for i in te])
        m["methods"]["poisson_only"] = {"accuracy": float(((pp >= 0.5) == (yte == 1)).mean()), "log_loss": _logloss(pp, yte)}
        rule = np.array([X[i]["astro_rule_over" if mk == "over25" else "astro_rule_btts"] for i in te])
        m["methods"]["astrology_scoreline_rule"] = {"accuracy": float((rule == yte).mean()), "log_loss": None}
        preds = {}
        for name, cols in (("statistics", STAT_COLS), ("statistics_plus_astrology", STAT_COLS + ASTRO_COLS),
                           ("astrology_only", ASTRO_COLS)):
            mdl = _model().fit(_mat(X, cols, tr), ytr)
            p = mdl.predict_proba(_mat(X, cols, te))[:, 1]
            preds[name] = p
            m["methods"][name] = {"accuracy": float(((p >= 0.5) == (yte == 1)).mean()), "log_loss": _logloss(p, yte)}
        # does astrology add anything? paired bootstrap of the per-match log-loss difference
        ll = lambda p: -(yte * np.log(np.clip(p, 1e-6, 1)) + (1 - yte) * np.log(np.clip(1 - p, 1e-6, 1)))
        d = ll(preds["statistics_plus_astrology"]) - ll(preds["statistics"])
        rng = np.random.default_rng(0)
        boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
        m["astrology_effect"] = {"log_loss_change": float(d.mean()), "ci95": [float(np.percentile(boots, 2.5)),
                                                                         float(np.percentile(boots, 97.5))]}
        helps = m["astrology_effect"]["ci95"][1] < 0
        chosen = "statistics_plus_astrology" if helps else "statistics"
        m["chosen"] = chosen
        m["strong_pick"] = _threshold(preds[chosen], yte)
        cols = STAT_COLS + ASTRO_COLS if helps else STAT_COLS
        models[mk] = {"cols": cols, "model": _model().fit(_mat(X, cols, fin), y[fin]), "strong_pick": m["strong_pick"],
                      "chosen": chosen, "test_accuracy": m["methods"][chosen]["accuracy"]}
        res["markets"][mk] = m
    _save({"version": version, "models": models, "metrics": res})
    res["predicted_pending"] = predict_pending(conn)
    return res


def _save(obj):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(obj, LATEST)
    if obj.get("version"):
        joblib.dump(obj, os.path.join(MODEL_DIR, f"goals_v{obj['version']}.joblib"))


def _load():
    try:
        return joblib.load(LATEST)
    except Exception:
        return {"version": None, "models": {}, "metrics": {}}


# ------------------------------------------------------------------ prediction
def predict_pending(conn, match_ids: list[str] | None = None) -> int:
    rows = load(conn)
    X = build_features(rows)
    art = _load()
    models = art.get("models", {})
    want = set(match_ids) if match_ids else None
    n = 0
    with conn.transaction():
        for r, f in zip(rows, X):
            if not r["pending"] or (want is not None and r["id"] not in want):
                continue
            out = {"model_version": art.get("version"), "trained": bool(models),
                   "xg_home": round(f["xg_h"], 2), "xg_away": round(f["xg_a"], 2),
                   "astrology": {"likely_score": r["likely"], "over25": bool(f["astro_rule_over"]),
                                 "btts": bool(f["astro_rule_btts"])},
                   "generated_at": datetime.now(timezone.utc).isoformat()}
            for mk in MARKETS:
                if mk in models:
                    md = models[mk]
                    p = float(md["model"].predict_proba(np.array([[f[c] for c in md["cols"]]]))[0, 1])
                    sp = md.get("strong_pick")
                    out[mk] = {"p": round(p, 3), "pick": p >= 0.5, "method": md["chosen"],
                               "strong": bool(sp and max(p, 1 - p) >= sp["threshold"]),
                               "test_accuracy": md["test_accuracy"]}
                else:
                    p = f["p_over_poisson"] if mk == "over25" else f["p_btts_poisson"]
                    out[mk] = {"p": round(float(p), 3), "pick": p >= 0.5, "method": "poisson_only", "strong": False,
                               "test_accuracy": None}
            conn.execute('UPDATE "Match" SET "goalsPrediction" = %s WHERE id = %s', (json.dumps(out), r["id"]))
            n += 1
    return n


def metrics():
    return _load().get("metrics", {})
