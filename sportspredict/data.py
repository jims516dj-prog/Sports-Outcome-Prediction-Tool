"""Loaders that convert public datasets into the canonical match schema."""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

DATA = os.environ.get("SP_DATA", os.path.join(os.path.dirname(__file__), "..", "data"))


def _finish(df):
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df.home_score.astype(float)
    df["away_score"] = df.away_score.astype(float)
    return df.sort_values("date", kind="stable").reset_index(drop=True)


def load_international():
    """martj42/international_results: every men's international since 1872."""
    df = pd.read_csv(os.path.join(DATA, "intl.csv"), parse_dates=["date"])
    df = df.rename(columns={"home_team": "home", "away_team": "away"})
    df["neutral"] = df.neutral.astype(str).str.upper().eq("TRUE").astype(int)
    df["friendly"] = df.tournament.eq("Friendly").astype(int)
    return _finish(df)


def load_club():
    """footballcsv: EPL, La Liga, Bundesliga 2012-13 .. 2019-20."""
    frames = []
    for f in sorted(glob.glob(os.path.join(DATA, "club_*.csv"))):
        d = pd.read_csv(f)
        sc = d["FT"].astype(str).str.extract(r"(\d+)\s*-\s*(\d+)").astype(float)
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(d["Date"], format="%a %b %d %Y", errors="coerce"),
            "home": d["Team 1"], "away": d["Team 2"],
            "home_score": sc[0], "away_score": sc[1],
            "league": os.path.basename(f).split("_")[1]}))
    df = pd.concat(frames).dropna(subset=["date"])
    df["neutral"] = 0
    return _finish(df)


def load_nba():
    """FiveThirtyEight nbaallelo.csv (1946-2015). One row per game, home perspective."""
    d = pd.read_csv(os.path.join(DATA, "nba.csv"))
    d = d[(d._iscopy == 0) & (d.lg_id == "NBA")]
    home = d.game_location.eq("H") | d.game_location.eq("N")
    out = pd.DataFrame({
        "date": pd.to_datetime(d.date_game, format="%m/%d/%Y"),
        "home": np.where(home, d.team_id, d.opp_id),
        "away": np.where(home, d.opp_id, d.team_id),
        "home_score": np.where(home, d.pts, d.opp_pts),
        "away_score": np.where(home, d.opp_pts, d.pts),
        "neutral": d.game_location.eq("N").astype(int).values,
        "ref_538_p": np.where(home, d.forecast, 1 - d.forecast),
    })
    return _finish(out)


def load_csv(path, sport, seed=0):
    """Generic user file in the canonical schema. For tennis, a Sackmann-style file
    (winner_name, loser_name, tourney_date, surface, winner_birth...) is also accepted
    and randomised into player1/player2."""
    df = pd.read_csv(path)
    if "winner_name" in df.columns:
        rng = np.random.default_rng(seed)
        flip = rng.random(len(df)) < 0.5
        w, l = df.winner_name.values, df.loser_name.values
        out = pd.DataFrame({
            "date": pd.to_datetime(df.tourney_date.astype(str), format="%Y%m%d"),
            "home": np.where(flip, l, w), "away": np.where(flip, w, l),
            "home_score": np.where(flip, 0, 1), "away_score": np.where(flip, 1, 0),
            "neutral": 1, "surface": df.get("surface")})
        for side, col in (("home", "birth"), ("away", "birth")):
            pass
        if "winner_dob" in df.columns:
            wd, ld = df.winner_dob.astype(str), df.loser_dob.astype(str)
            out["home_birth"] = np.where(flip, ld, wd)
            out["away_birth"] = np.where(flip, wd, ld)
        if {"odds_winner", "odds_loser"} <= set(df.columns):
            out["odds_home"] = np.where(flip, df.odds_loser, df.odds_winner)
            out["odds_away"] = np.where(flip, df.odds_winner, df.odds_loser)
        return _finish(out)
    df["date"] = pd.to_datetime(df["date"])
    if "neutral" not in df:
        df["neutral"] = 1 if sport == "tennis" else 0
    return _finish(df)


def load_top5():
    """openfootball: EPL, Bundesliga, La Liga, Serie A, Ligue 1 2010-2025 with kickoff times."""
    from astro_backtest import load_timed_matches
    return load_timed_matches()


LOADERS = {"intl": ("soccer", load_international, 2005),
           "top5": ("soccer", load_top5, 2012),
           "club": ("soccer", load_club, 2015),
           "nba": ("basketball", load_nba, 1995)}
