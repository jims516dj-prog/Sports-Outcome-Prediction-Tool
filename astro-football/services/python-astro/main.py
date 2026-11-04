"""Astrology microservice (FastAPI): charts, engines, synthesis, geo/timezone, ML training.

run: uvicorn main:app --port 8001
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Literal, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import chart as C
import engines as EN
import ml_pipeline as ML
import reference as R
import sources as SRC
import wikipedia_geo as G
from reference import COLOR_PLANET, NUMBER_PLANET, SPORT_PRESETS, reduce_digit, relation

DB_URL = os.environ.get("DATABASE_URL", "postgresql://astro:astro@localhost:5432/astro_football").split("?")[0]
app = FastAPI(title="astro-football python service", version="1.0")
scheduler = BackgroundScheduler()
scheduler.start()


def parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


# ------------------------------------------------------------------ models
class Founding(BaseModel):
    date: Optional[str] = None            # YYYY-MM-DD
    time: Optional[str] = None            # HH:MM local at founding place
    lat: Optional[float] = None
    long: Optional[float] = None
    tz: Optional[str] = None


class AnalyzeIn(BaseModel):
    team_a: str
    team_b: str
    kickoff_gmt: str                      # ISO, UTC
    lat: float
    long: float
    sport: str = "football"
    context: Literal["league", "knockout", "final", "friendly"] = "league"
    odds_a: float
    odds_b: float
    odds_draw: Optional[float] = None
    founding_a: Optional[Founding] = None
    founding_b: Optional[Founding] = None
    has_captain_data: bool = False
    captain_a_jersey: Optional[int] = None
    captain_b_jersey: Optional[int] = None
    team_a_jersey_color: Optional[str] = None
    team_b_jersey_color: Optional[str] = None
    toggles: dict = Field(default_factory=dict)
    engine_weights: dict = Field(default_factory=dict)


class ChartIn(BaseModel):
    date: str
    time_gmt: str
    lat: float
    long: float
    ayanamsha: Optional[Literal["lahiri", "krishnamurti", "tropical"]] = None


# ------------------------------------------------------------------ helpers
def natal(fd: Optional[Founding]):
    if not fd or not fd.date:
        return None
    d = date.fromisoformat(fd.date[:10])
    birth_utc = None
    if fd.time and fd.lat is not None and fd.long is not None:
        tz = fd.tz or G.tz_at(fd.lat, fd.long)
        from zoneinfo import ZoneInfo
        hh, mm = map(int, fd.time[:5].split(":"))
        try:
            birth_utc = datetime(d.year, d.month, d.day, hh, mm, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
        except Exception:                                   # pre-1900 zones etc.
            birth_utc = datetime(d.year, d.month, d.day, hh, mm, tzinfo=timezone.utc)
    pts = C.natal_points(birth_utc, d, fd.lat, fd.long)
    return pts | {"has_time": birth_utc is not None,
                  "moon_sign_name": R.SIGNS[pts["moon_sign"]],
                  "asc_sign_name": R.SIGNS[pts["asc_sign"]] if pts["asc_sign"] is not None else None}


def build_input(a: AnalyzeIn, c: C.Chart):
    preset = SPORT_PRESETS.get(a.sport, SPORT_PRESETS["football"])
    clear = abs(a.odds_a - a.odds_b) > 0.05
    fav_side = "A" if (a.odds_a <= a.odds_b or not clear) else "B"
    fav, und = (a.team_a, a.team_b) if fav_side == "A" else (a.team_b, a.team_a)
    na, nb = natal(a.founding_a), natal(a.founding_b)
    pick = lambda xa, xb: (xa, xb) if fav_side == "A" else (xb, xa)
    cap_f, cap_u = pick(a.captain_a_jersey, a.captain_b_jersey)
    col_f, col_u = pick(a.team_a_jersey_color, a.team_b_jersey_color)
    nat_f, nat_u = pick(na, nb)
    return {"team_a": a.team_a, "team_b": a.team_b, "fav_side": fav_side, "fav_name": fav, "und_name": und,
            "clear_favourite": clear, "draw_possible": a.context in preset["draw_contexts"],
            "extra_time": a.context in ("knockout", "final"), "moon_range": preset["moon_range_deg"],
            "extra_time_deg": preset["extra_time_deg"], "goal_divisor": preset["goal_divisor"],
            "has_captain_data": a.has_captain_data, "captain_fav": cap_f, "captain_und": cap_u,
            "color_fav": col_f, "color_und": col_u, "natal_fav": nat_f, "natal_und": nat_u,
            "natal_a": na, "natal_b": nb, "sport": a.sport, "context": a.context,
            "odds_a": a.odds_a, "odds_b": a.odds_b}


def jersey_relation(inp, c):
    if not inp["has_captain_data"] or not inp["captain_fav"]:
        return "none"
    rel = relation(NUMBER_PLANET[reduce_digit(inp["captain_fav"])], NUMBER_PLANET[reduce_digit(c.dt_utc.day)])
    return {1: "friend", 0: "neutral", -1: "enemy"}[rel]


def run_analysis(a: AnalyzeIn, only: Optional[str] = None):
    ko = parse_utc(a.kickoff_gmt)
    c = C.compute_chart(ko, a.lat, a.long)
    inp = build_input(a, c)
    tg = EN._toggles(a.toggles)
    warnings = []
    r = k = f = None
    if tg["engines"].get("rao", True) and only in (None, "rao"):
        r = EN.rao(c, inp, a.toggles)
    if tg["engines"].get("chokoisky", True) and only in (None, "chokoisky"):
        k = EN.chokoisky(c, inp, a.toggles)
    frawley_notice = None
    if not inp["clear_favourite"]:
        frawley_notice = ("Frawley's event-chart method requires a clear favourite. With equal odds, this engine is "
                          "disabled. Rao and Chokoisky engines still run.")
        warnings.append("No clear favourite (odds within ±0.05) - Frawley disabled; Team A taken as Native")
    elif tg["engines"].get("frawley", True) and only in (None, "frawley"):
        f = EN.frawley(c, inp, a.toggles)
    s = EN.sandhi(c)
    warnings += s["warnings"]
    if not (inp["natal_a"] and inp["natal_b"]):
        missing = [n for n, x in ((a.team_a, inp["natal_a"]), (a.team_b, inp["natal_b"])) if not x]
        warnings.append(f"Missing founding chart for {', '.join(missing)} - Rao's Nations' Charts phase limited")
    syn = EN.synthesise(r, k, f, s, inp, a.engine_weights)
    loc = G.gmt_to_local(ko, a.lat, a.long)
    d1c, d9c = C.chart_chokoisky(c)
    res = {"input": {k2: v for k2, v in inp.items()}, "rao": r, "chokoisky": k, "frawley": f,
           "frawley_notice": frawley_notice, "sandhi": s, "synthesis": syn, "warnings": warnings, "local": loc,
           "charts": {"rao": C.chart_rao(c), "chokoisky": d1c, "chokoisky_d9": d9c, "frawley": C.chart_frawley(c)}}
    res["jersey_relation"] = jersey_relation(inp, c)
    res["ml_features"] = ML.extract_features(res, inp)
    return res


# ------------------------------------------------------------------ routes
@app.get("/health")
def health():
    return {"ok": True, "swisseph": C.swe.version, "ephe": C.EPHE}


@app.post("/chart")
def chart(body: ChartIn):
    ko = parse_utc(f"{body.date}T{body.time_gmt}")
    c = C.compute_chart(ko, body.lat, body.long)
    d1, d9 = C.chart_chokoisky(c)
    out = {"rao": C.chart_rao(c), "chokoisky": d1, "chokoisky_d9": d9, "frawley": C.chart_frawley(c)}
    if body.ayanamsha == "tropical":
        return {"frawley": out["frawley"]}
    if body.ayanamsha == "krishnamurti":
        return {"sublords": d1["sublords"]}
    return out


@app.post("/analyze")
def analyze(body: AnalyzeIn):
    try:
        return run_analysis(body)
    except Exception as e:  # surface errors to the UI
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.post("/engine/{name}")
def engine(name: Literal["rao", "chokoisky", "frawley"], body: AnalyzeIn):
    res = run_analysis(body, only=name)
    return {"engine": res[name], "notice": res.get("frawley_notice") if name == "frawley" else None,
            "chart": res["charts"]["chokoisky" if name == "chokoisky" else name], "sandhi": res["sandhi"]}


@app.post("/natal")
def natal_route(body: Founding):
    return natal(body) or {}


@app.get("/geo/lookup")
def geo_lookup(name: str, wiki_title: Optional[str] = None):
    return G.lookup(name, wiki_title)


@app.get("/tz")
def tz(lat: float, long: float, gmt: Optional[str] = None, local: Optional[str] = None):
    if gmt:
        return G.gmt_to_local(parse_utc(gmt), lat, long)
    if local:
        return G.local_to_gmt(datetime.fromisoformat(local), lat, long)
    return {"timezone": G.tz_at(lat, long)}


@app.get("/reference")
def reference():
    return R.all_tables() | {"toggles_default": R.DEFAULT_TOGGLES, "colors": list(COLOR_PLANET)}


class PlanIn(BaseModel):
    mode: Literal["history", "refresh"]
    leagues: list[str]
    from_season: Optional[str] = None
    to_season: Optional[str] = None
    api_key: Optional[str] = None


@app.get("/sources/leagues")
def sources_leagues():
    return SRC.leagues_info()


@app.post("/sources/plan")
def sources_plan(body: PlanIn):
    try:
        return SRC.plan(body.mode, body.leagues, body.from_season, body.to_season, body.api_key or None)
    except Exception as e:
        raise HTTPException(502, f"{type(e).__name__}: {e}")


@app.post("/ml/train")
def ml_train(config: dict | None = None):
    try:
        return ML.train(DB_URL, config or {})
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.get("/ml/schedule")
def ml_schedule_get():
    job = scheduler.get_job("nightly")
    return {"enabled": job is not None, "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None}


@app.post("/ml/schedule")
def ml_schedule_set(body: dict):
    if scheduler.get_job("nightly"):
        scheduler.remove_job("nightly")
    if body.get("enabled"):
        tz = body.get("timezone") or "UTC"
        scheduler.add_job(lambda: ML.train(DB_URL, body.get("config") or {}), CronTrigger(hour=2, minute=0, timezone=tz),
                          id="nightly", replace_existing=True)
    return ml_schedule_get()


if os.environ.get("NIGHTLY_RETRAIN", "1") == "1":
    scheduler.add_job(lambda: ML.train(DB_URL, {}), CronTrigger(hour=2, minute=0), id="nightly", replace_existing=True)
