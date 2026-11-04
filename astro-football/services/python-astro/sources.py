"""Match data sources for the data-sync feature.

* openfootball/football.json (no key): every season back to 2010, fixtures and results with
  local kickoff times. Community-maintained, so the current season can lag by weeks.
* football-data.org v4 (free API key): current-season fixtures with exact UTC kickoff times
  and results within minutes of full time.

Both are normalised to one record per fixture, keyed by league + season + home + away
(each pairing happens once per league season, so the key survives postponements).
Neither source has bookmaker odds, so pre-match odds are derived from an Elo rating.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

import teams as T
import wikipedia_geo as G

UA = {"User-Agent": "astro-football/1.0 (fixture sync)"}
OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{league}.json"
FDORG = "https://api.football-data.org/v4/competitions/{code}/matches"
HERE = os.path.dirname(__file__)
CACHE_DIR = os.path.join(HERE, "cache")
VENUE_CACHE = os.path.join(CACHE_DIR, "venues.json")

LEAGUES = {
    "en.1": {"name": "Premier League (England)", "fdorg": "PL", "first": "2010-11"},
    "de.1": {"name": "Bundesliga (Germany)", "fdorg": "BL1", "first": "2010-11"},
    "es.1": {"name": "La Liga (Spain)", "fdorg": "PD", "first": "2012-13"},
    "it.1": {"name": "Serie A (Italy)", "fdorg": "SA", "first": "2013-14"},
    "fr.1": {"name": "Ligue 1 (France)", "fdorg": "FL1", "first": "2014-15"},
    "en.2": {"name": "Championship (England)", "fdorg": "ELC", "first": "2014-15"},
    "nl.1": {"name": "Eredivisie (Netherlands)", "fdorg": "DED", "first": "2018-19"},
    "pt.1": {"name": "Primeira Liga (Portugal)", "fdorg": "PPL", "first": "2018-19"},
}

_DROP = {"fc", "afc", "cf", "sc", "ac", "ssc", "us", "ss", "cd", "ud", "sd", "rc", "rcd", "ca", "calcio", "club",
         "de", "da", "do", "the", "sv", "vfl", "vfb", "tsg", "fsv", "bc", "cfc", "sco", "osc", "losc", "hsc", "ogc"}


# ------------------------------------------------------------------ seasons & names
def season_of(d: date) -> str:
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def season_range(first: str, last: str):
    a, b = int(first[:4]), int(last[:4])
    return [f"{y}-{str(y + 1)[2:]}" for y in range(a, b + 1)]


def team_key(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t not in _DROP and not t.isdigit()]
    return " ".join(toks)


_KEY2NAME = {team_key(n): n for n in T.COORDS}


def resolve(name: str, league: str) -> str:
    """Canonical club name: alias table, then exact key, then unique token containment."""
    c = T.canon(name, league)
    if c in T.COORDS:
        return c
    k = team_key(c)
    if k in _KEY2NAME:
        return _KEY2NAME[k]
    toks = set(k.split())
    hits = [n for kk, n in _KEY2NAME.items() if kk and (set(kk.split()) <= toks or toks <= set(kk.split()))]
    return hits[0] if len(hits) == 1 else c


def ext_id(league: str, season: str, home: str, away: str) -> str:
    return f"{league}:{season}:{team_key(home)}:{team_key(away)}"


# ------------------------------------------------------------------ fetchers
def _cached_json(url: str, cache_name: str | None):
    if cache_name:
        p = os.path.join(CACHE_DIR, cache_name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    for attempt in range(3):
        try:
            r = httpx.get(url, headers=UA, timeout=30, follow_redirects=True)
            break
        except httpx.TransportError:
            if attempt == 2:
                raise
    if r.status_code == 404:
        return None
    r.raise_for_status()
    js = r.json()
    if cache_name:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(os.path.join(CACHE_DIR, cache_name), "w", encoding="utf-8") as f:
            json.dump(js, f)
    return js


def parse_openfootball(js: dict, league: str, season: str):
    out = []
    matches = js.get("matches") or [m for r in js.get("rounds", []) for m in r.get("matches", [])]
    for m in matches:
        home, away = resolve(m["team1"], league), resolve(m["team2"], league)
        sc = m.get("score")
        ft = sc.get("ft") if isinstance(sc, dict) else None
        if ft is None and m.get("score1") is not None:
            ft = [m["score1"], m["score2"]]
        ko = None
        if m.get("time"):
            hh, mm = map(int, m["time"][:5].split(":"))
            tz = ZoneInfo(T.TEAM_TZ.get(home, T.LEAGUE_TZ.get(league, "UTC")))
            off = re.search(r"UTC([+-]\d+)", m["time"])
            if off:                                   # explicit offset, e.g. "18:00 UTC+3"
                tz = timezone(timedelta(hours=int(off.group(1))))
            ko = datetime.fromisoformat(m["date"]).replace(hour=hh, minute=mm, tzinfo=tz).astimezone(timezone.utc)
        out.append({"id": ext_id(league, season, home, away), "league": league, "season": season,
                    "date": m["date"], "kickoff_utc": ko.strftime("%Y-%m-%dT%H:%M") if ko else None,
                    "home": home, "away": away,
                    "score": [int(ft[0]), int(ft[1])] if ft else None,
                    "status": "finished" if ft else "scheduled", "round": m.get("round", ""),
                    "source": "openfootball"})
    return out


def fetch_openfootball(league: str, season: str, current: str):
    js = _cached_json(OPENFOOTBALL.format(season=season, league=league),
                      None if season >= current else f"of_{season}_{league}.json")
    return parse_openfootball(js, league, season) if js else []


FD_STATUS = {"FINISHED": "finished", "AWARDED": "finished", "SCHEDULED": "scheduled", "TIMED": "scheduled",
             "POSTPONED": "postponed", "SUSPENDED": "postponed", "CANCELLED": "cancelled",
             "IN_PLAY": "live", "PAUSED": "live", "LIVE": "live"}


def parse_fdorg(js: dict, league: str):
    out = []
    for m in js.get("matches", []):
        home = resolve(m["homeTeam"].get("name") or m["homeTeam"].get("shortName") or "", league)
        away = resolve(m["awayTeam"].get("name") or m["awayTeam"].get("shortName") or "", league)
        start = (m.get("season") or {}).get("startDate") or js.get("filters", {}).get("season")
        season = season_of(date.fromisoformat(str(start)[:10])) if start and len(str(start)) >= 10 else \
            (f"{start}-{str(int(start) + 1)[2:]}" if start else season_of(date.fromisoformat(m["utcDate"][:10])))
        ko = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone(timezone.utc)
        status = FD_STATUS.get(m.get("status", ""), "scheduled")
        ft = (m.get("score") or {}).get("fullTime") or {}
        score = [int(ft["home"]), int(ft["away"])] if status == "finished" and ft.get("home") is not None else None
        out.append({"id": ext_id(league, season, home, away), "league": league, "season": season,
                    "date": ko.strftime("%Y-%m-%d"), "kickoff_utc": ko.strftime("%Y-%m-%dT%H:%M"),
                    "home": home, "away": away, "score": score, "status": status if score or status != "finished"
                    else "scheduled", "round": f"Matchday {m.get('matchday')}" if m.get("matchday") else "",
                    "source": "football-data.org"})
    return out


def fetch_fdorg(league: str, season: str, api_key: str):
    code = LEAGUES[league]["fdorg"]
    r = httpx.get(FDORG.format(code=code), params={"season": season[:4]},
                  headers={**UA, "X-Auth-Token": api_key}, timeout=30)
    if r.status_code in (400, 403):
        raise PermissionError(f"football-data.org refused {code}: {r.json().get('message', r.text)[:200]}")
    if r.status_code == 429:
        raise RuntimeError("football-data.org rate limit reached (10 requests/minute on the free plan) - try again in a minute")
    r.raise_for_status()
    return parse_fdorg(r.json(), league)


# ------------------------------------------------------------------ Elo-derived odds
def add_elo_odds(matches, k=20.0, hfa=60.0):
    """Pre-match fair odds from an Elo rating updated in kickoff order (finished matches only)."""
    elo = defaultdict(lambda: 1500.0)
    key = lambda m: (m["kickoff_utc"] or m["date"] + "T23:59")
    for m in sorted(matches, key=key):
        h, a = team_key(m["home"]), team_key(m["away"])
        d = elo[h] - elo[a] + hfa
        p = 1 / (1 + 10 ** (-d / 400))
        pd = max(0.12, 0.28 - 0.35 * abs(p - 0.5))
        m["odds"] = [round(1 / (p * (1 - pd)), 2), round(1 / pd, 2), round(1 / ((1 - p) * (1 - pd)), 2)]
        if m["score"] is not None:
            hs, as_ = m["score"]
            res = 1.0 if hs > as_ else (0.5 if hs == as_ else 0.0)
            elo[h] += k * (res - p)
            elo[a] -= k * (res - p)


# ------------------------------------------------------------------ venues
def _venue_cache():
    try:
        with open(VENUE_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def venue_for(team: str, cache: dict):
    if team in T.COORDS:
        lat, lon = T.COORDS[team]
        return {"name": f"{team} (home ground)", "lat": lat, "long": lon, "source": "seed"}
    if team in cache:
        return cache[team]
    v = None
    try:
        r = G.lookup(f"{team} stadium")
        if r.get("lat") is not None:
            v = {"name": r.get("canonicalName") or f"{team} (home ground)", "lat": r["lat"], "long": r["long"],
                 "source": r["source"]}
    except Exception:
        v = None
    if v:
        cache[team] = v          # failed lookups are retried on the next run
    return v


# ------------------------------------------------------------------ plan
def plan(mode: str, leagues: list[str], from_season: str | None = None, to_season: str | None = None,
         api_key: str | None = None, today: date | None = None):
    """Return normalised fixtures (with Elo odds and venues) for the web app to apply.

    mode "history": finished matches in [from_season, to_season].
    mode "refresh": every match of the current season (the app applies its own date window).
    """
    today = today or datetime.now(timezone.utc).date()
    current = season_of(today)
    warnings, used = [], set()
    leagues = [lg for lg in leagues if lg in LEAGUES]
    if mode == "history":
        first = from_season or current
        last = min(to_season or current, current)
        wanted = set(season_range(first, last))
        fetch = season_range(f"{int(first[:4]) - 2}-00", last)          # two seasons of Elo warm-up
    else:
        wanted = {current}
        fetch = season_range(f"{int(current[:4]) - 2}-00", current)
    all_matches = []
    for lg in leagues:
        by_id = {}
        for s in fetch:
            if s < LEAGUES[lg]["first"]:
                continue
            try:
                ms = fetch_openfootball(lg, s, current)
            except Exception as e:
                warnings.append(f"openfootball {lg} {s}: {type(e).__name__}")
                continue
            if ms:
                used.add("openfootball")
            elif s in wanted:
                warnings.append(f"openfootball has no {LEAGUES[lg]['name']} file for {s}")
            for m in ms:
                by_id[m["id"]] = m
        if mode == "refresh" and api_key:
            try:
                for m in fetch_fdorg(lg, current, api_key):
                    prev = by_id.get(m["id"])
                    if prev and prev["score"] and not m["score"]:
                        m["score"], m["status"] = prev["score"], "finished"
                    by_id[m["id"]] = m
                used.add("football-data.org")
            except Exception as e:
                warnings.append(f"football-data.org {LEAGUES[lg]['name']}: {e}")
        all_matches.extend(by_id.values())
    add_elo_odds(all_matches)
    cache = _venue_cache()
    out, no_venue = [], set()
    for m in all_matches:
        if m["season"] not in wanted:
            continue
        if mode == "history" and m["status"] != "finished":
            continue
        v = venue_for(m["home"], cache)
        if not v:
            no_venue.add(m["home"])
            continue
        m["venue"] = v
        out.append(m)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(VENUE_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    if no_venue:
        warnings.append("No stadium location found for: " + ", ".join(sorted(no_venue))
                        + " - add the team's default venue in Settings, then refresh again")
    out.sort(key=lambda m: m["kickoff_utc"] or m["date"])
    return {"matches": out, "warnings": warnings, "sources": sorted(used), "current_season": current,
            "today": today.isoformat()}


def leagues_info(today: date | None = None):
    current = season_of(today or datetime.now(timezone.utc).date())
    return {"leagues": [{"code": k, **v} for k, v in LEAGUES.items()], "current_season": current,
            "last_complete_season": season_range(f"{int(current[:4]) - 1}-00", current)[0]}
