"""Offline tests for the data-sync sources (run: python -m pytest tests or python tests/test_sources.py)."""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import httpx  # noqa: E402

import sources as S  # noqa: E402

FD_SAMPLE = {  # shape of GET /v4/competitions/PL/matches?season=2026 (football-data.org docs)
    "filters": {"season": "2026"},
    "competition": {"code": "PL", "name": "Premier League"},
    "matches": [
        {"id": 1, "utcDate": "2026-09-20T13:00:00Z", "status": "FINISHED", "matchday": 5,
         "season": {"startDate": "2026-08-22", "endDate": "2027-05-30"},
         "homeTeam": {"name": "Arsenal FC", "shortName": "Arsenal"}, "awayTeam": {"name": "Chelsea FC"},
         "score": {"winner": "HOME_TEAM", "duration": "REGULAR", "fullTime": {"home": 2, "away": 1}}},
        {"id": 2, "utcDate": "2026-11-07T17:30:00Z", "status": "TIMED", "matchday": 11,
         "season": {"startDate": "2026-08-22", "endDate": "2027-05-30"},
         "homeTeam": {"name": "Manchester City FC"}, "awayTeam": {"name": "Liverpool FC"},
         "score": {"winner": None, "fullTime": {"home": None, "away": None}}},
        {"id": 3, "utcDate": "2026-11-01T15:00:00Z", "status": "POSTPONED", "matchday": 10,
         "season": {"startDate": "2026-08-22", "endDate": "2027-05-30"},
         "homeTeam": {"name": "Tottenham Hotspur FC"}, "awayTeam": {"name": "Everton FC"},
         "score": {"fullTime": {"home": None, "away": None}}},
    ],
}


def test_parse_fdorg():
    ms = {m["home"]: m for m in S.parse_fdorg(FD_SAMPLE, "en.1")}
    assert ms["Arsenal"]["score"] == [2, 1] and ms["Arsenal"]["status"] == "finished"
    assert ms["Arsenal"]["id"] == "en.1:2026-27:arsenal:chelsea"
    assert ms["Manchester City"]["kickoff_utc"] == "2026-11-07T17:30" and ms["Manchester City"]["status"] == "scheduled"
    assert ms["Tottenham Hotspur"]["status"] == "postponed" and ms["Tottenham Hotspur"]["score"] is None


def test_parse_openfootball_local_time():
    js = {"matches": [{"round": "Matchday 1", "date": "2026-08-22", "time": "15:00", "team1": "Arsenal FC",
                       "team2": "Chelsea FC", "score": {"ft": [1, 1]}},
                      {"round": "Matchday 2", "date": "2026-12-26", "team1": "Chelsea FC", "team2": "Arsenal FC"}]}
    a, b = S.parse_openfootball(js, "en.1", "2026-27")
    assert a["kickoff_utc"] == "2026-08-22T14:00"          # BST -> UTC
    assert a["score"] == [1, 1] and b["kickoff_utc"] is None and b["status"] == "scheduled"


def test_refresh_merges_football_data_org(monkeypatch=None):
    real_get = httpx.get

    def fake_get(url, *a, **kw):
        if "football-data.org" in url:
            return httpx.Response(200, json=FD_SAMPLE, request=httpx.Request("GET", url))
        return real_get(url, *a, **kw)
    S.httpx.get = fake_get
    try:
        p = S.plan("refresh", ["en.1"], api_key="test", today=date(2026, 11, 4))
    finally:
        S.httpx.get = real_get
    by = {m["id"]: m for m in p["matches"]}
    assert "football-data.org" in p["sources"]
    m = by["en.1:2026-27:manchester city:liverpool"]
    assert m["source"] == "football-data.org" and m["kickoff_utc"] == "2026-11-07T17:30"
    assert all(len(x["odds"]) == 3 for x in p["matches"])


def test_name_resolution():
    for raw, lg, want in [("FC Internazionale Milano", "it.1", "Inter"), ("SL Benfica", "pt.1", "Benfica"),
                          ("LOSC Lille", "fr.1", "Lille OSC"), ("Feyenoord", "nl.1", "Feyenoord Rotterdam"),
                          ("Club Atlético de Madrid", "es.1", "Atlético Madrid"), ("Paris FC", "fr.1", "Paris FC")]:
        assert S.resolve(raw, lg) == want, (raw, S.resolve(raw, lg))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
