"""Bulk-import historical matches (openfootball JSON) through the app's own API.

Each match is posted to POST /api/matches as a historical (post-hoc) record, so it is
analysed by the same engines and stored exactly like a hand-entered match.

The source data have kickoff times but no bookmaker odds. Odds are therefore derived
from a pre-match Elo rating (fair odds, no margin) and the record notes say so.

usage:
  python scripts/import_history.py --data ../data/of --from 2023-07-01 [--to 2024-06-30]
         [--leagues en.1,de.1] [--limit 500] [--workers 8] [--base http://localhost:3000]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

sys.path.insert(0, os.path.dirname(__file__))
import club_venues as CV  # noqa: E402


def load(data_dir, leagues):
    rows = []
    for f in sorted(glob.glob(os.path.join(data_dir, "20*.json"))):
        lg = os.path.basename(f).split("_")[1][:-5]
        if leagues and lg not in leagues:
            continue
        for m in json.load(open(f))["matches"]:
            sc = m.get("score", {})
            if not (isinstance(sc, dict) and sc.get("ft") and m.get("time")):
                continue
            h, a = CV.canon(m["team1"], lg), CV.canon(m["team2"], lg)
            tz = ZoneInfo(CV.TEAM_TZ.get(h, CV.LEAGUE_TZ[lg]))
            hh, mm = map(int, m["time"][:5].split(":"))
            ko = datetime.fromisoformat(m["date"]).replace(hour=hh, minute=mm, tzinfo=tz).astimezone(timezone.utc)
            rows.append({"ko": ko, "lg": lg, "home": h, "away": a, "hs": sc["ft"][0], "as": sc["ft"][1],
                         "round": m.get("round", "")})
    rows.sort(key=lambda r: r["ko"])
    return rows


def with_elo_odds(rows, k=20.0, hfa=60.0):
    elo = defaultdict(lambda: 1500.0)
    for r in rows:
        d = elo[r["home"]] - elo[r["away"]] + hfa
        p = 1 / (1 + 10 ** (-d / 400))
        pd = max(0.12, 0.28 - 0.35 * abs(p - 0.5))
        ph, pa = p * (1 - pd), (1 - p) * (1 - pd)
        r["odds"] = (round(1 / ph, 2), round(1 / pd, 2), round(1 / pa, 2))
        res = 1.0 if r["hs"] > r["as"] else (0.5 if r["hs"] == r["as"] else 0.0)
        delta = k * (res - p)
        elo[r["home"]] += delta
        elo[r["away"]] -= delta
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "of"))
    ap.add_argument("--from", dest="date_from", default="2023-07-01")
    ap.add_argument("--to", dest="date_to", default=None)
    ap.add_argument("--leagues", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--base", default="http://localhost:3000")
    a = ap.parse_args()
    rows = with_elo_odds(load(a.data, set(filter(None, a.leagues.split(",")))))
    lo = datetime.fromisoformat(a.date_from).replace(tzinfo=timezone.utc)
    hi = datetime.fromisoformat(a.date_to).replace(tzinfo=timezone.utc) if a.date_to else None
    rows = [r for r in rows if r["ko"] >= lo and (hi is None or r["ko"] <= hi)]
    if a.limit:
        rows = rows[: a.limit]
    print(f"importing {len(rows)} matches (Elo warm-up used all seasons)")
    client = httpx.Client(base_url=a.base, timeout=60)
    venues = {v["name"]: v for v in client.get("/api/venues").json()}
    teams = {t["name"]: t for t in client.get("/api/teams").json()}

    def venue_for(team):
        dv = teams.get(team, {}).get("defaultVenue")
        if dv and dv in venues:
            v = venues[dv]
            return {"name": v["name"], "lat": v["lat"], "long": v["long"], "source": v["coordinateSource"]}
        lat, lon = CV.COORDS[team]
        return {"name": f"{team} (home ground)", "lat": lat, "long": lon, "source": "seed"}

    def post(r):
        oh, od, oa = r["odds"]
        body = {"historical": True, "input": {
            "sport": "football", "context": "league", "teamA": r["home"], "teamB": r["away"],
            "kickoffGMT": r["ko"].strftime("%Y-%m-%dT%H:%M"), "venue": venue_for(r["home"]),
            "oddsA": oh, "oddsB": oa, "oddsDraw": od, "scoreA": r["hs"], "scoreB": r["as"], "status": "completed",
            "notes": f"Imported from openfootball ({r['lg']} {r['round']}); odds derived from Elo ratings, not bookmaker odds"}}
        res = client.post("/api/matches", json=body)
        if res.status_code != 200:
            raise RuntimeError(res.text[:200])

    done = failed = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(post, r) for r in rows]
        for f in as_completed(futs):
            try:
                f.result()
                done += 1
            except Exception as e:
                failed += 1
                if failed <= 5:
                    print("  failed:", e)
            if (done + failed) % 250 == 0:
                print(f"  {done + failed}/{len(rows)}")
    print(f"done: {done} imported, {failed} failed")


if __name__ == "__main__":
    main()
