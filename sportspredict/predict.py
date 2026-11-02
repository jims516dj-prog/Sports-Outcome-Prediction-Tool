"""Predict upcoming matches.

usage:
  python predict.py SPORT HISTORY.csv FIXTURES.csv [--esoteric] [--target 0.70]
  python predict.py basketball nba  FIXTURES.csv          # bundled history: intl | club | nba

HISTORY: played matches in the canonical schema (see engine.py).
FIXTURES: date, home, away [, neutral, friendly, surface, odds_home, odds_draw,
          odds_away, home_birth, away_birth]

Soccer/hockey fixtures also get an OVER/UNDER total-goals pick (optional fixture
columns odds_over, odds_under; --ou-line to change the line).

Output: probabilities, pick, and a HIGH-CONFIDENCE flag for matches whose model
confidence is above the threshold that historically (out-of-sample, walk-forward)
delivered >= target accuracy.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import data
import engine as E
import esoteric


def confidence_threshold(P, y, classes, target, recent_years, dates):
    ok = ~np.isnan(P[:, 0]) & (dates.dt.year.values >= dates.dt.year.max() - recent_years)
    conf, hit = P[ok].max(1), P[ok].argmax(1) == np.searchsorted(classes, y[ok])
    for t in np.arange(0.40, 0.96, 0.005):
        sel = conf >= t
        if sel.sum() >= 100 and hit[sel].mean() >= target + 0.01:  # 1-pt safety margin
            return float(t), float(hit[sel].mean()), float(sel.mean())
    return None, None, 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sport", choices=list(E.SPORTS))
    ap.add_argument("history")
    ap.add_argument("fixtures")
    ap.add_argument("--esoteric", action="store_true",
                    help="include astrology/numerology features (backtests show no useful gain)")
    ap.add_argument("--target", type=float, default=0.70)
    ap.add_argument("--recent-years", type=int, default=6)
    ap.add_argument("--astro-engines", action="store_true",
                    help="soccer: also run the Rao / Chokoisky / Frawley engines (needs kickoff_utc "
                         "and lat/lon columns, or a home club listed in venues.py; requires pyswisseph)")
    ap.add_argument("--ou-line", type=float, default=None,
                    help="over/under goals line (default 2.5 soccer, 5.5 hockey)")
    a = ap.parse_args()

    hist = data.LOADERS[a.history][1]() if a.history in data.LOADERS else data.load_csv(a.history, a.sport)
    fx = pd.read_csv(a.fixtures)
    fx["date"] = pd.to_datetime(fx["date"])
    for c, v in (("neutral", 1 if a.sport == "tennis" else 0), ("friendly", 0)):
        if c not in fx:
            fx[c] = v

    X = E.build_features(hist, a.sport, esoteric_on=a.esoteric).drop(columns=["_idx"]).fillna(0.0)
    y = E.outcome(hist, a.sport)
    F_all = E.build_features(hist, a.sport, esoteric_on=a.esoteric, fixtures=fx)
    which = "stat+eso" if a.esoteric else "stat"
    # a feature (e.g. market odds) is only usable if both history and fixtures have it
    cols = [c for c in E.feature_sets(X.columns)[which] if c in F_all.columns]
    F = F_all.reindex(columns=cols).fillna(0.0)

    start = max(hist.date.dt.year.min() + 1, hist.date.dt.year.max() - a.recent_years)
    P_oos, classes = E.walk_forward(X, y, hist.date, cols, start, min_train=300)
    thr, thr_acc, thr_cov = confidence_threshold(P_oos, y, classes, a.target, a.recent_years, hist.date)
    m = E.metrics(P_oos, y, classes)

    model = E.make_model().fit(X[cols].values, y)
    P = model.predict_proba(F.values)
    labels = {0: "HOME/P1", 1: "DRAW", 2: "AWAY/P2"}
    print(f"\nOut-of-sample backtest (last {a.recent_years} seasons): accuracy {m['accuracy']:.1%} "
          f"over {m['n']} matches, log-loss {m['log_loss']:.3f}")
    if thr:
        print(f"High-confidence filter: p >= {thr:.3f} -> {thr_acc:.1%} accuracy on {thr_cov:.0%} of matches\n")
    else:
        print(f"No confidence level reached {a.target:.0%} accuracy historically.\n")
    for i, r in fx.reset_index(drop=True).iterrows():
        probs = {labels[c]: P[i, j] for j, c in enumerate(model.classes_)}
        pick = max(probs, key=probs.get)
        flag = "HIGH-CONFIDENCE" if thr and probs[pick] >= thr else "low-confidence"
        ps = "  ".join(f"{k} {v:.1%}" for k, v in probs.items())
        print(f"{r.date.date()}  {r.home} vs {r.away}:  {ps}  -> {pick} [{flag}]")
        print(f"            sky: {esoteric.describe_sky(r.date)}")

    if E.SPORTS[a.sport].goal_model:
        predict_totals(a, hist, X, F_all, fx, which)
    if a.astro_engines:
        astro_panel(fx, F_all)


def astro_panel(fx, F_all):
    """Classical sports-astrology verdicts (Rao, Chokoisky, Frawley) for each fixture.
    The favourite (1st house) is the side the statistical model rates higher."""
    from datetime import datetime, timezone
    import astro_engines as AE
    import venues as V
    print("\nASTROLOGY ENGINES (Rao / Chokoisky / Frawley). Backtest on 23,701 matches found no "
          "edge (see README); shown for research only.")
    for i, r in fx.reset_index(drop=True).iterrows():
        if "kickoff_utc" not in fx or pd.isna(r.get("kickoff_utc")):
            print(f"{r.home} vs {r.away}: skipped - needs a kickoff_utc column (e.g. 2026-11-14T19:45)")
            continue
        if {"lat", "lon"} <= set(fx.columns) and pd.notna(r.get("lat")):
            lat, lon = float(r.lat), float(r.lon)
        elif r.home in V.COORDS:
            lat, lon = V.COORDS[r.home]
        else:
            print(f"{r.home} vs {r.away}: skipped - needs lat/lon columns for the venue")
            continue
        ko = pd.Timestamp(r.kickoff_utc)
        ko = (ko.tz_localize("UTC") if ko.tzinfo is None else ko.tz_convert("UTC")).to_pydatetime()
        p_home = F_all.elo_p.iloc[i]
        fav_home = p_home >= 0.5
        fav, und = (r.home, r.away) if fav_home else (r.away, r.home)
        res = AE.analyse(ko, lat, lon, fav, und, draw_possible=not bool(r.get("knockout", 0)),
                         clear_favourite=abs(p_home - 0.5) >= 0.02)
        name = {"fav": fav, "und": und, "draw": "DRAW"}
        fr = res["frawley"]
        print(f"{ko:%Y-%m-%d %H:%M}Z  {r.home} vs {r.away}  (favourite: {fav})")
        print(f"   Rao       -> {name[res['rao']['verdict']]:<22} points diff {res['rao']['diff']:+.1f}")
        print(f"   Chokoisky -> {name[res['chokoisky']['verdict']]:<22} total {res['chokoisky']['total']:+.1f} "
              f"({res['chokoisky']['confidence']}), goal diff ~{res['chokoisky']['goal_diff']}")
        if fr:
            top = "; ".join(x for _, _, x in fr["testimonies"][:3]) or "no testimony - default to favourite"
            print(f"   Frawley   -> {name[fr['verdict']]:<22} score {fr['score']:+.1f}  [{top}]")
        else:
            print("   Frawley   -> disabled (no clear favourite)")
        flags = [k for k, v in res["sandhi"].items() if v and k != "any"]
        print(f"   Consensus -> {name[res['consensus']]} ({res['pattern']}, astro confidence {res['confidence']}%)"
              + (f"  sandhi: {', '.join(flags)}" if flags else ""))


def predict_totals(a, hist, X, F_all, fx, which):
    line = a.ou_line if a.ou_line is not None else (2.5 if a.sport == "soccer" else 5.5)
    Xt = E.add_totals_features(X, line)
    Ft = E.add_totals_features(F_all.fillna(0.0), line)
    cols = [c for c in E.totals_feature_sets(Xt.columns)[which] if c in Ft.columns]
    y = E.totals_target(hist, line)
    start = max(hist.date.dt.year.min() + 1, hist.date.dt.year.max() - a.recent_years)
    P_oos, classes = E.walk_forward(Xt, y, hist.date, cols, start, min_train=300)
    thr, thr_acc, thr_cov = confidence_threshold(P_oos, y, classes, a.target, a.recent_years, hist.date)
    m = E.metrics(P_oos, y, classes)
    model = E.make_model().fit(Xt[cols].values, y)
    P = model.predict_proba(Ft.reindex(columns=cols).fillna(0.0).values)
    j_over = list(model.classes_).index(1)
    print(f"\nOVER/UNDER {line} goals. Out-of-sample backtest: accuracy {m['accuracy']:.1%} over {m['n']} "
          f"matches (over rate {y[~np.isnan(P_oos[:, 0])].mean():.1%})")
    if thr:
        print(f"High-confidence filter: p >= {thr:.3f} -> {thr_acc:.1%} accuracy on {thr_cov:.0%} of matches\n")
    else:
        print(f"No confidence level reached {a.target:.0%} accuracy historically.\n")
    for i, r in fx.reset_index(drop=True).iterrows():
        po = P[i, j_over]
        pick, conf = ("OVER", po) if po >= 0.5 else ("UNDER", 1 - po)
        flag = "HIGH-CONFIDENCE" if thr and conf >= thr else "low-confidence"
        xg = Ft.iloc[i]
        print(f"{r.date.date()}  {r.home} vs {r.away}:  OVER {po:.1%}  UNDER {1 - po:.1%}  -> {pick} {line} [{flag}]"
              f"   (expected goals {xg.ou_xg_h:.2f}-{xg.ou_xg_a:.2f}, Poisson P(over) {xg.ou_poisson_p_over:.1%})")


if __name__ == "__main__":
    main()
