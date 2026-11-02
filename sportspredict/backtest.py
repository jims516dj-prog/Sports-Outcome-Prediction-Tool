"""Walk-forward backtest + esoteric-feature ablation and permutation test.

usage: python backtest.py intl|club|nba [--ou-only]   (bundled datasets)
       python backtest.py path/to/file.csv SPORT START_YEAR [--ou-only]
Soccer/hockey also run an over/under backtest (2.5 / 5.5 goals).
"""
from __future__ import annotations

import json
import sys

import numpy as np

import data
import engine as E


def run(df, sport, start_year, n_perm=10, report_name="report"):
    X = E.build_features(df, sport)
    X = X.drop(columns=["_idx"]).fillna(0.0)
    y = E.outcome(df, sport)
    dates = df.date
    sets = E.feature_sets(X.columns)
    res, preds = {}, {}
    for name, cols in sets.items():
        P, classes = E.walk_forward(X, y, dates, cols, start_year)
        preds[name] = P
        res[name] = E.metrics(P, y, classes)
        res[name]["accuracy_at_coverage"] = E.coverage_curve(P, y, classes)
        res[name]["selective_70"] = E.selective_accuracy(P, y, classes, dates, 0.70)

    ok = ~np.isnan(preds["stat"][:, 0])
    yy = y[ok]
    # naive baselines
    counts = np.bincount(np.searchsorted(classes, yy), minlength=len(classes))
    res["baseline_majority_class"] = float(counts.max() / counts.sum())
    res["baseline_higher_elo"] = float(((X.elo_diff.values[ok] > 0) == (yy == 0)).mean()) if not E.SPORTS[sport].draws else \
        float(np.where(X.elo_diff.values[ok] > 0, 0, 2).__eq__(yy).mean())
    if "ref_538_p" in df:
        p538 = df.ref_538_p.values[ok]
        res["reference_538_elo_accuracy"] = float(((p538 > 0.5) == (yy == 0)).mean())

    # Does astrology/numerology add information beyond the statistics?
    ll_s = E.per_match_logloss(preds["stat"][ok], yy, classes)
    ll_e = E.per_match_logloss(preds["stat+eso"][ok], yy, classes)
    d, lo, hi = E.bootstrap_diff(ll_e, ll_s)
    real_gain = -d
    # permutation null: shuffle esoteric rows across matches, refit
    rng = np.random.default_rng(1)
    eso_cols = [c for c in X.columns if c.startswith("eso_")]
    null = []
    for _ in range(n_perm):
        Xp = X.copy()
        Xp[eso_cols] = X[eso_cols].values[rng.permutation(len(X))]
        Pp, _ = E.walk_forward(Xp, y, dates, sets["stat+eso"], start_year)
        null.append(E.per_match_logloss(Ps := Pp[ok], yy, classes).mean())
    null_gain = ll_s.mean() - np.array(null)
    res["esoteric_test"] = {
        "logloss_change_adding_eso (neg=better)": d, "ci95": [lo, hi],
        "accuracy_change": res["stat+eso"]["accuracy"] - res["stat"]["accuracy"],
        "eso_only_accuracy_minus_majority": res["eso_only"]["accuracy"] - res["baseline_majority_class"],
        "permutation_p_value": float((1 + (null_gain >= real_gain).sum()) / (1 + n_perm)),
        "n_permutations": n_perm,
    }
    with open(f"{report_name}.json", "w") as f:
        json.dump(res, f, indent=2)
    return res


def run_totals(df, sport, start_year, line=2.5, n_perm=10, report_name="report_ou"):
    """Over/under `line` total goals: walk-forward backtest + esoteric ablation."""
    X = E.build_features(df, sport).drop(columns=["_idx"]).fillna(0.0)
    X = E.add_totals_features(X, line)
    y = E.totals_target(df, line)
    dates = df.date
    sets = E.totals_feature_sets(X.columns)
    res, preds = {"line": line}, {}
    for name, cols in sets.items():
        P, classes = E.walk_forward(X, y, dates, cols, start_year)
        preds[name] = P
        res[name] = E.metrics(P, y, classes)
        res[name]["accuracy_at_coverage"] = E.coverage_curve(P, y, classes)
        res[name]["selective_70"] = E.selective_accuracy(P, y, classes, dates, 0.70)
    ok = ~np.isnan(preds["stat"][:, 0])
    yy = y[ok]
    res["over_rate"] = float(yy.mean())
    res["baseline_majority_class"] = float(max(yy.mean(), 1 - yy.mean()))
    res["baseline_poisson_only"] = float(((X.ou_poisson_p_over.values[ok] > 0.5) == (yy == 1)).mean())
    # how good are the picks on each side?
    P = preds["stat"][ok]
    pick_over = P[:, 1] > 0.5
    res["over_picks"] = {"share": float(pick_over.mean()), "accuracy": float(yy[pick_over].mean()) if pick_over.any() else None}
    res["under_picks"] = {"share": float((~pick_over).mean()), "accuracy": float(1 - yy[~pick_over].mean()) if (~pick_over).any() else None}
    ll_s = E.per_match_logloss(preds["stat"][ok], yy, classes)
    ll_e = E.per_match_logloss(preds["stat+eso"][ok], yy, classes)
    d, lo, hi = E.bootstrap_diff(ll_e, ll_s)
    rng = np.random.default_rng(1)
    eso_cols = [c for c in sets["stat+eso"] if c.startswith("eso_")]
    null = []
    for _ in range(n_perm):
        Xp = X.copy()
        Xp[eso_cols] = X[eso_cols].values[rng.permutation(len(X))]
        Pp, _ = E.walk_forward(Xp, y, dates, sets["stat+eso"], start_year)
        null.append(E.per_match_logloss(Pp[ok], yy, classes).mean())
    null_gain = ll_s.mean() - np.array(null)
    res["esoteric_test"] = {
        "logloss_change_adding_eso (neg=better)": d, "ci95": [lo, hi],
        "accuracy_change": res["stat+eso"]["accuracy"] - res["stat"]["accuracy"],
        "eso_only_accuracy_minus_majority": res["eso_only"]["accuracy"] - res["baseline_majority_class"],
        "permutation_p_value": float((1 + (null_gain >= -d).sum()) / (1 + n_perm)),
        "n_permutations": n_perm,
    }
    with open(f"{report_name}.json", "w") as f:
        json.dump(res, f, indent=2)
    return res


if __name__ == "__main__":
    if sys.argv[1] in data.LOADERS:
        sport, loader, start = data.LOADERS[sys.argv[1]]
        df = loader()
        name = sys.argv[1]
    else:
        sport, start = sys.argv[2], int(sys.argv[3])
        df = data.load_csv(sys.argv[1], sport)
        name = sport
    if name == "intl":
        df = df[df.date.dt.year >= 1990].reset_index(drop=True)  # ratings warm-up from 1990
    if "--ou-only" not in sys.argv:
        r = run(df, sport, start, report_name=f"report_{name}")
        print(json.dumps(r, indent=2))
    if sport in ("soccer", "hockey"):
        line = 2.5 if sport == "soccer" else 5.5
        r = run_totals(df, sport, start, line, report_name=f"report_{name}_ou")
        print(json.dumps(r, indent=2))
