"""Does the Rao / Chokoisky / Frawley methodology add an edge?

Runs the three engines on every top-5-league match 2010-2025 that has a recorded
kickoff time (openfootball), then tests them five ways:

 A. raw accuracy of each engine and of the synthesised consensus vs simple baselines
 B. calibration test: when an engine picks the UNDERDOG, does the underdog win more
    often than the statistical model expected?  (the cleanest test of "edge")
 C. walk-forward model: statistics vs statistics + all engine features
    (match result and over/under 2.5), bootstrap CI + permutation test
 D. the specification's own ML combination discovery (section 12.3), run honestly:
    combinations are mined on past seasons and then scored on the next season
 E. the same engine features on their own (no statistics)

usage: python astro_backtest.py [--perms 20]
"""
from __future__ import annotations

import glob
import itertools
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2_contingency

import engine as E
import venues as V

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE = os.path.join(DATA, "astro_engine_features.csv")


# ------------------------------------------------------------------ data
def load_timed_matches():
    rows = []
    for f in sorted(glob.glob(os.path.join(DATA, "of", "20*.json"))):
        lg = os.path.basename(f).split("_")[1][:-5]
        for m in json.load(open(f))["matches"]:
            sc = m.get("score", {})
            if not (isinstance(sc, dict) and sc.get("ft") and m.get("time")):
                continue
            h, a = V.canon(m["team1"], lg), V.canon(m["team2"], lg)
            tz = ZoneInfo(V.TEAM_TZ.get(h, V.LEAGUE_TZ[lg]))
            hh, mm = map(int, m["time"][:5].split(":"))
            local = datetime.fromisoformat(m["date"]).replace(hour=hh, minute=mm, tzinfo=tz)
            rows.append({"date": pd.Timestamp(m["date"]), "kickoff_utc": local.astimezone(ZoneInfo("UTC")),
                         "league": lg, "home": h, "away": a,
                         "home_score": sc["ft"][0], "away_score": sc["ft"][1]})
    df = pd.DataFrame(rows)
    df["neutral"] = 0
    missing = sorted(set(df.home) - set(V.COORDS))
    if missing:
        raise SystemExit(f"no coordinates for: {missing}")
    return df.sort_values(["date", "kickoff_utc"], kind="stable").reset_index(drop=True)


def engine_features(df, fav_is_home, clear_fav):
    import astro_engines as A
    if os.path.exists(CACHE):
        c = pd.read_csv(CACHE)
        if len(c) == len(df):
            return c
    out = []
    for i, r in enumerate(df.itertuples()):
        lat, lon = V.COORDS[r.home]
        fav, und = (r.home, r.away) if fav_is_home[i] else (r.away, r.home)
        a = A.analyse(r.kickoff_utc.to_pydatetime(), lat, lon, fav, und,
                      draw_possible=True, clear_favourite=bool(clear_fav[i]))
        rr, k, f, s = a["rao"], a["chokoisky"], a["frawley"], a["sandhi"]
        row = {"rao_diff": rr["diff"], "rao_verdict": rr["verdict"],
               "chok_total": k["total"], "chok_verdict": k["verdict"], "chok_conf": k["confidence"],
               "chok_d9": int(k["d9_cusp_planet"]), "chok_sky": int(k["sky"]),
               "chok_sublord_diff": k["sublord_diff"], "chok_nama_fav": k["nama_pada_fav"],
               "chok_nama_und": k["nama_pada_und"],
               "fraw_verdict": f["verdict"] if f else "disabled", "fraw_score": f["score"] if f else 0.0,
               "fraw_n": f["n_testimonies"] if f else 0, "fraw_late": int(f["late_goal"]) if f else 0,
               "fraw_l1_on_7": int(f["lord1_on_7th"]) if f else 0, "fraw_pluto_1": int(f["pluto_on_1st"]) if f else 0,
               "fraw_goals_winner": f["goals_winner"] if f else 0,
               "consensus": a["consensus"], "agreement": a["agreement"], "pattern": a["pattern"],
               "astro_confidence": a["confidence"], "sandhi": int(s["any"]),
               "rao_saturn8": int(rr["saturn_8th"])}
        row.update({f"chok_{k2}": v for k2, v in k["rows"].items()})
        out.append(row)
        if i % 2000 == 0:
            print(f"  engines: {i}/{len(df)}", file=sys.stderr)
    c = pd.DataFrame(out)
    c.to_csv(CACHE, index=False)
    return c


# ------------------------------------------------------------------ helpers
def outcome_fav(df, fav_is_home):
    hw, aw = df.home_score > df.away_score, df.home_score < df.away_score
    return np.where(hw, np.where(fav_is_home, "fav", "und"), np.where(aw, np.where(fav_is_home, "und", "fav"), "draw"))


def astro_model_features(A, fav_is_home):
    s = np.where(fav_is_home, 1.0, -1.0)
    v = lambda col: np.select([A[col] == "fav", A[col] == "und"], [1.0, -1.0], 0.0)
    d = lambda col: (A[col] == "draw").astype(float)
    X = pd.DataFrame({
        "astro_rao_diff": s * A.rao_diff, "astro_chok_total": s * A.chok_total,
        "astro_fraw_score": s * A.fraw_score,
        "astro_rao_pick": s * v("rao_verdict"), "astro_chok_pick": s * v("chok_verdict"),
        "astro_fraw_pick": s * v("fraw_verdict"), "astro_consensus_pick": s * v("consensus"),
        "astro_rao_draw": d("rao_verdict"), "astro_chok_draw": d("chok_verdict"),
        "astro_fraw_draw": d("fraw_verdict"), "astro_consensus_draw": d("consensus"),
        "astro_fraw_l1_on_7": s * A.fraw_l1_on_7, "astro_fraw_pluto_1": s * A.fraw_pluto_1,
        "astro_nama": s * (A.chok_nama_fav - A.chok_nama_und),
        "astro_conf_x_pick": s * v("consensus") * A.astro_confidence / 100,
    })
    for c in [c for c in A.columns if c.startswith("chok_") and c[5:] in (
            "victory_houses", "sky_pky", "d1_cusps", "d9_cusps", "nama_pada", "sublords", "nakshatra_tara", "planetary_war")]:
        X["astro_" + c] = s * A[c]
    # non-directional (used for over/under)
    T = pd.DataFrame({"astro_abs_chok": A.chok_total.abs(), "astro_chok_goal_diff": (A.chok_total.abs() / 3).round(),
                      "astro_fraw_n": A.fraw_n, "astro_fraw_goals": A.fraw_goals_winner,
                      "astro_fraw_late": A.fraw_late, "astro_sandhi": A.sandhi, "astro_d9": A.chok_d9,
                      "astro_sky": A.chok_sky, "astro_abs_rao": A.rao_diff.abs(),
                      "astro_agreement": A.agreement, "astro_confidence": A.astro_confidence / 100})
    return X, T


def ab_test(X, y, dates, base_cols, extra_cols, start, n_perm, seed=1):
    P0, cl = E.walk_forward(X, y, dates, base_cols, start)
    P1, _ = E.walk_forward(X, y, dates, base_cols + extra_cols, start)
    ok = ~np.isnan(P0[:, 0])
    l0, l1 = E.per_match_logloss(P0[ok], y[ok], cl), E.per_match_logloss(P1[ok], y[ok], cl)
    d, lo, hi = E.bootstrap_diff(l1, l0)
    rng, null = np.random.default_rng(seed), []
    for _ in range(n_perm):
        Xp = X.copy()
        Xp[extra_cols] = X[extra_cols].values[rng.permutation(len(X))]
        Pp, _ = E.walk_forward(Xp, y, dates, base_cols + extra_cols, start)
        null.append(E.per_match_logloss(Pp[ok], y[ok], cl).mean())
    gain, null_gain = -d, l0.mean() - np.array(null)
    m0, m1 = E.metrics(P0, y, cl), E.metrics(P1, y, cl)
    return {"n": int(ok.sum()), "acc_stats": m0["accuracy"], "acc_stats_plus_astro": m1["accuracy"],
            "logloss_stats": m0["log_loss"], "logloss_plus_astro": m1["log_loss"],
            "logloss_change (neg=better)": d, "ci95": [lo, hi],
            "acc_top30pct_stats": E.coverage_curve(P0, y, cl)[0.3],
            "acc_top30pct_plus_astro": E.coverage_curve(P1, y, cl)[0.3],
            "permutation_p": float((1 + (null_gain >= gain).sum()) / (1 + n_perm)), "n_perm": n_perm}, P0, ok, cl


# ------------------------------------------------------------------ D. spec 12.3 combination mining
def conditions(A):
    c = {}
    for col in ("rao_verdict", "chok_verdict", "fraw_verdict", "pattern", "consensus", "chok_conf"):
        for val in A[col].unique():
            c[f"{col}={val}"] = (A[col] == val).values
    c["agreement=3"] = (A.agreement == 3).values
    for col in ("chok_d9", "chok_sky", "fraw_l1_on_7", "fraw_pluto_1", "fraw_late", "sandhi", "rao_saturn8",
                "chok_nama_fav", "chok_nama_und"):
        c[f"{col}"] = (A[col] == 1).values
    c["rao_diff>8"] = (A.rao_diff.abs() > 8).values
    c["rao_diff>5"] = (A.rao_diff.abs() > 5).values
    c["chok_total>9"] = (A.chok_total.abs() > 9).values
    c["sublord_dominance>9"] = (A.chok_sublord_diff.abs() > 9).values
    c["d9_jupiter_like_fav"] = (A.chok_d9_cusps > 0).values
    return {k: v for k, v in c.items() if v.any()}


def mine(conds, correct, idx, n_total, max_len):
    """Spec 12.3 + 12.5 thresholds (dataset > 500 -> min n 20, acc >= 75%)."""
    min_n, min_acc = (20, 0.75) if n_total > 500 else ((15, 0.70) if n_total > 100 else (10, 0.65))
    keys, kept = list(conds), []
    base = correct[idx].mean()
    for L in range(1, max_len + 1):
        for combo in itertools.combinations(keys, L):
            m = idx.copy()
            for k in combo:
                m &= conds[k]
            n = m.sum()
            if n < min_n:
                continue
            acc = correct[m].mean()
            if acc < min_acc:
                continue
            k_in, k_out = correct[m].sum(), correct[idx & ~m].sum()
            n_out = (idx & ~m).sum()
            if n_out == 0:
                continue
            p = chi2_contingency([[k_in, n - k_in], [k_out, n_out - k_out]])[1]
            if p < 0.05:
                kept.append((combo, int(n), float(acc), min(3.0, 1 + (acc - 0.5) * 2)))
    return kept, base


def combination_backtest(A, df, actual, fav_actual_win):
    conds = conditions(A)
    correct = (A.consensus.values == actual)
    season = np.where(df.date.dt.month >= 7, df.date.dt.year, df.date.dt.year - 1)
    res = []
    for yr in range(2012, season.max() + 1):
        train, test = season < yr, season == yr
        kept, base = mine(conds, correct, train, train.sum(), max_len=3 if train.sum() > 200 else 2)
        if not kept:
            res.append({"season": int(yr), "combos": 0})
            continue
        hit = np.zeros(len(A), bool)
        for combo, *_ in kept:
            m = test.copy()
            for k in combo:
                m &= conds[k]
            hit |= m
        res.append({"season": int(yr), "combos": len(kept),
                    "train_acc_mean": float(np.mean([x[2] for x in kept])),
                    "test_matches_flagged": int(hit.sum()),
                    "test_consensus_acc": float(correct[hit].mean()) if hit.any() else None,
                    "test_pick_favourite_acc_same_matches": float(fav_actual_win[hit].mean()) if hit.any() else None})
    return res


# ------------------------------------------------------------------ main
def main(n_perm=20):
    df = load_timed_matches()
    print(f"{len(df)} timed matches, {df.date.min().date()} .. {df.date.max().date()}", file=sys.stderr)
    X = E.build_features(df, "soccer", esoteric_on=False).drop(columns=["_idx"]).fillna(0.0)
    X = E.add_totals_features(X, 2.5)
    fav_is_home = X.elo_p.values >= 0.5
    clear_fav = np.abs(X.elo_p.values - 0.5) >= 0.02
    A = engine_features(df, fav_is_home, clear_fav)
    actual = outcome_fav(df, fav_is_home)
    R = {"n_matches": len(df), "period": [str(df.date.min().date()), str(df.date.max().date())]}

    # A. raw accuracy (evaluate on 2012+ to match the model's out-of-sample window)
    ev = (df.date.dt.year >= 2012).values
    a = actual[ev]
    R["A_raw_accuracy"] = {
        "always_pick_favourite": float((a == "fav").mean()),
        "rao": float((A.rao_verdict.values[ev] == a).mean()),
        "chokoisky": float((A.chok_verdict.values[ev] == a).mean()),
        "frawley (when enabled)": float((A.fraw_verdict.values[ev & (A.fraw_verdict != "disabled").values] ==
                                         actual[ev & (A.fraw_verdict != "disabled").values]).mean()),
        "consensus": float((A.consensus.values[ev] == a).mean()),
        "consensus_all3_agree": float((A.consensus.values[ev & (A.agreement == 3).values] ==
                                       actual[ev & (A.agreement == 3).values]).mean()),
        "share_all3_agree": float((A.agreement.values[ev] == 3).mean()),
        "outcome_shares": {k: float((a == k).mean()) for k in ("fav", "draw", "und")},
    }
    for eng in ("rao_verdict", "chok_verdict", "fraw_verdict", "consensus"):
        R["A_raw_accuracy"][f"{eng}_pick_shares"] = {k: float((A[eng].values[ev] == k).mean())
                                                    for k in ("fav", "draw", "und", "disabled")}

    # C. walk-forward models
    y = E.outcome(df, "soccer")
    AX, AT = astro_model_features(A, fav_is_home)
    XX = pd.concat([X, AX, AT], axis=1)
    stat = E.feature_sets(X.columns)["stat"]
    res1x2, P0, ok, cl = ab_test(XX, y, df.date, stat, list(AX.columns), 2012, n_perm)
    R["C_match_result"] = res1x2
    yt = E.totals_target(df, 2.5)
    st_ou = E.totals_feature_sets(X.columns)["stat"]
    R["C_over_under_2.5"], *_ = ab_test(XX, yt, df.date, st_ou, list(AT.columns), 2012, n_perm)
    # E. engine features alone
    Pa, cla = E.walk_forward(XX, y, df.date, list(AX.columns) + ["neutral"], 2012)
    R["E_engines_only_model_accuracy"] = E.metrics(Pa, y, cla)["accuracy"]
    R["E_majority_class"] = float(np.bincount(y[ok]).max() / ok.sum())

    # B. calibration: underdog / draw / favourite picks vs model expectation
    Pm = np.full((len(df), 3), np.nan)
    Pm[ok] = P0[ok]
    p_fav = np.where(fav_is_home, Pm[:, 0], Pm[:, 2])
    p_und = np.where(fav_is_home, Pm[:, 2], Pm[:, 0])
    p_draw = Pm[:, 1]
    B = {}
    for eng in ("rao_verdict", "chok_verdict", "fraw_verdict", "consensus"):
        for pick, pexp in (("und", p_und), ("draw", p_draw), ("fav", p_fav)):
            m = ok & (A[eng].values == pick)
            if m.sum() < 30:
                continue
            k, n, e = int((actual[m] == pick).sum()), int(m.sum()), float(np.nanmean(pexp[m]))
            B[f"{eng}:{pick}"] = {"n": n, "actual_rate": k / n, "model_expected": e,
                                  "excess": k / n - e, "p_value": binomtest(k, n, e).pvalue}
    R["B_calibration"] = B

    # D. spec ML combination discovery, walk-forward
    R["D_combination_mining"] = combination_backtest(A, df, actual, (actual == "fav"))
    return R


if __name__ == "__main__":
    n_perm = int(sys.argv[sys.argv.index("--perms") + 1]) if "--perms" in sys.argv else 20
    R = main(n_perm)
    with open("report_astro_engines.json", "w") as f:
        json.dump(R, f, indent=2, default=float)
    print(json.dumps(R, indent=2, default=float))
