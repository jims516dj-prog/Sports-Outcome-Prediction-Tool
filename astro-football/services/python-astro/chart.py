"""Chart computation (spec section 4) on the Swiss Ephemeris.

One physical moment yields three charts:
  rao       - sidereal (Lahiri), whole-sign houses
  chokoisky - sidereal (Lahiri; Krishnamurti for sublords), Placidus, D1 + D9
  frawley   - tropical, Placidus
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import swisseph as swe

from reference import (DIG_BALA_HOUSE, NAKSHATRAS, SIGN_LORD, SIGNS, VIM, VIM_YEARS, dignity,
                       PLANET_ORDER)

EPHE = os.environ.get("SE_EPHE_PATH", os.path.join(os.path.dirname(__file__), "ephe"))
swe.set_ephe_path(EPHE)

SU, MO, MA, ME, JU, VE, SA, RA, KE, UR, NE, PL, CH, CE, UK, GU = (
    "Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke", "Ur", "Ne", "Pl", "Ch", "Ce", "Uk", "Gu")
SWE_ID = {SU: swe.SUN, MO: swe.MOON, MA: swe.MARS, ME: swe.MERCURY, JU: swe.JUPITER,
          VE: swe.VENUS, SA: swe.SATURN, UR: swe.URANUS, NE: swe.NEPTUNE, PL: swe.PLUTO,
          CH: swe.CHIRON, CE: swe.CERES}
GRAHAS = [SU, MO, MA, ME, JU, VE, SA, RA, KE]


def norm(x):
    return x % 360.0


def sep(a, b):
    d = abs(norm(a) - norm(b)) % 360
    return min(d, 360 - d)


def signed(a, b):
    """b - a in (-180, 180]."""
    return (b - a + 180) % 360 - 180


def fmt_deg(x):
    x = norm(x)
    s, d = int(x // 30), x % 30
    return f"{int(d):02d}°{int(round((d % 1) * 60)) % 60:02d}′ {SIGNS[s]}"


@dataclass
class Chart:
    jd: float
    lat: float
    lon: float
    dt_utc: datetime
    trop: dict = field(default_factory=dict)
    speed: dict = field(default_factory=dict)
    cusps: list = field(default_factory=list)       # Placidus, tropical; index 0 = 1st
    asc: float = 0.0
    mc: float = 0.0
    ay_lahiri: float = 0.0
    ay_kp: float = 0.0
    sunrise: float | None = None
    sunset: float | None = None

    def sid(self, p, kp=False):
        return norm(self.trop[p] - (self.ay_kp if kp else self.ay_lahiri))

    def sid_pt(self, x, kp=False):
        return norm(x - (self.ay_kp if kp else self.ay_lahiri))

    def sign(self, p):
        return int(self.sid(p) // 30)

    @staticmethod
    def trop_sign(x):
        return int(norm(x) // 30)

    def house_of(self, x):
        for i in range(12):
            a, b = self.cusps[i], self.cusps[(i + 1) % 12]
            if norm(x - a) < norm(b - a):
                return i + 1
        return 12

    def retro(self, p):
        return self.speed.get(p, 1) < 0

    @property
    def lagna_sid_sign(self):
        return int(self.sid_pt(self.asc) // 30)


def _calc(jd, pid):
    try:
        r = swe.calc_ut(jd, pid, swe.FLG_SWIEPH | swe.FLG_SPEED)[0]
    except swe.Error:
        try:
            r = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)[0]
        except swe.Error:            # asteroid outside the bundled ephemeris range
            return float("nan"), 0.0
    return r[0], r[3]


def julday(dt_utc: datetime) -> float:
    """Dates before the Gregorian reform (15 Oct 1582) are taken as Julian-calendar dates,
    as historical founding dates are recorded."""
    dt_utc = dt_utc.astimezone(timezone.utc)
    h = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    cal = swe.GREG_CAL if (dt_utc.year, dt_utc.month, dt_utc.day) >= (1582, 10, 15) else swe.JUL_CAL
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h, cal)


def compute_chart(dt_utc: datetime, lat: float, lon: float) -> Chart:
    jd = julday(dt_utc)
    c = Chart(jd, lat, lon, dt_utc)
    for p, pid in SWE_ID.items():
        c.trop[p], c.speed[p] = _calc(jd, pid)
    c.trop[RA], c.speed[RA] = _calc(jd, swe.MEAN_NODE)
    c.trop[KE], c.speed[KE] = norm(c.trop[RA] + 180), c.speed[RA]
    c.trop["TrueNode"], _ = _calc(jd, swe.TRUE_NODE)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b"P")
    c.cusps, c.asc, c.mc = list(cusps[:12]), ascmc[0], ascmc[1]
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    c.ay_lahiri = swe.get_ayanamsa_ut(jd)
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    c.ay_kp = swe.get_ayanamsa_ut(jd)
    c.trop[UK] = norm(c.trop[SU] - 30)                     # Upaketu = Sun - 30 deg
    c.trop[GU], c.sunrise, c.sunset = _gulika(c)
    c.speed[UK] = c.speed[SU]
    c.speed[GU] = 1.0
    return c


def _rise_set(jd0, lat, lon, rsmi):
    try:
        res, t = swe.rise_trans(jd0, swe.SUN, rsmi, (lon, lat, 0.0))
        return t[0] if res == 0 else None
    except Exception:
        return None


def _gulika(c: Chart):
    """Gulika = ascendant at the start of Saturn's 1/8 portion of the day (or night)."""
    jd = c.jd
    rise = _rise_set(jd - 1, c.lat, c.lon, swe.CALC_RISE)
    while rise is not None:
        nxt = _rise_set(rise + 0.01, c.lat, c.lon, swe.CALC_RISE)
        if nxt is None or nxt > jd:
            break
        rise = nxt
    if rise is None:
        return norm(c.trop[SU] + 180), None, None
    sset = _rise_set(rise, c.lat, c.lon, swe.CALC_SET)
    nrise = _rise_set(sset, c.lat, c.lon, swe.CALC_RISE)
    vedic_day = (int(math.floor(rise + 0.5 + c.lon / 360)) + 1) % 7      # 0 = Sunday
    if jd < sset:
        start, length, first = rise, (sset - rise) / 8, vedic_day
    else:
        start, length, first = sset, (nrise - sset) / 8, (vedic_day + 4) % 7
    k = next(i for i in range(7) if (first + i) % 7 == 6)
    return swe.houses_ex(start + k * length, c.lat, c.lon, b"P")[1][0], rise, sset


# ------------------------------------------------------------------ helpers shared by engines
def nak_index(sid_lon):
    return int(norm(sid_lon) // (360 / 27))


def nak_lord(sid_lon):
    return VIM[nak_index(sid_lon) % 9]


def sub_lord(sid_lon):
    nak_len = 360 / 27
    start = VIM.index(nak_lord(sid_lon))
    pos = (norm(sid_lon) % nak_len) / nak_len * 120
    acc = 0.0
    for i in range(9):
        p = VIM[(start + i) % 9]
        acc += VIM_YEARS[p]
        if pos < acc:
            return p
    return VIM[(start + 8) % 9]


def d9(sid_lon):
    return norm(sid_lon * 9)


def antiscion(x):
    return norm(180 - x)


def fortuna(c: Chart):
    return norm(c.asc + c.trop[MO] - c.trop[SU])


def tithi(c: Chart):
    return int(norm(c.trop[MO] - c.trop[SU]) // 12) + 1


def vedic_weekday(c: Chart):
    """Vedic day runs sunrise to sunrise; returns 0 = Sunday."""
    base = c.sunrise if c.sunrise is not None and c.sunrise <= c.jd else c.jd
    return (int(math.floor(base + 0.5 + c.lon / 360)) + 1) % 7


DAY_LORDS = [SU, MO, MA, ME, JU, VE, SA]
DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ------------------------------------------------------------------ JSON snapshots (POST /chart)
def _planet_rows(c: Chart, mode: str, house_fn):
    rows = {}
    for p in PLANET_ORDER:
        if math.isnan(c.trop[p]):
            continue                                   # e.g. Chiron outside ephemeris range
        lon = c.trop[p] if mode == "tropical" else c.sid(p)
        s = int(lon // 30)
        rows[p] = {"lon": round(lon, 4), "sign": SIGNS[s], "deg": round(lon % 30, 4), "pos": fmt_deg(lon),
                   "house": house_fn(p), "speed": round(c.speed.get(p, 0.0), 4), "retrograde": c.retro(p),
                   "nakshatra": NAKSHATRAS[nak_index(c.sid(p))],
                   "dignity": {2: "exalted", 1: "own sign", -1: "debilitated"}.get(dignity(p, s), "")
                   if mode != "tropical" or p in GRAHAS else ""}
    return rows


def _common(c: Chart):
    sid_moon = c.sid(MO)
    wars = []
    for i, a in enumerate((MA, ME, JU, VE, SA)):
        for b in (MA, ME, JU, VE, SA)[i + 1:]:
            if sep(c.trop[a], c.trop[b]) <= 1.0:
                wars.append([a, b, round(sep(c.trop[a], c.trop[b]), 3)])
    comb = [{"planet": p, "distance": round(sep(c.trop[p], c.trop[SU]), 3),
             "cazimi": sep(c.trop[p], c.trop[SU]) <= 17 / 60}
            for p in (MO, MA, ME, JU, VE, SA) if sep(c.trop[p], c.trop[SU]) <= 8.5]
    wd = vedic_weekday(c)
    return {"nakshatra_of_moon": NAKSHATRAS[nak_index(sid_moon)], "tithi": tithi(c),
            "day_of_week": DAY_NAMES[wd], "day_lord": DAY_LORDS[wd],
            "planetary_wars": wars, "combustions": comb,
            "speeds": {p: round(c.speed.get(p, 0), 4) for p in PLANET_ORDER},
            "sunrise_jd": c.sunrise, "sunset_jd": c.sunset}


def chart_rao(c: Chart):
    lag = c.lagna_sid_sign
    return {"variant": "rao", "zodiac": "sidereal (Lahiri)", "houses_system": "whole sign",
            "ayanamsha": round(c.ay_lahiri, 5), "ascendant_deg": round(c.sid_pt(c.asc), 4),
            "ascendant": fmt_deg(c.sid_pt(c.asc)),
            "houses": [{"house": i + 1, "sign": SIGNS[(lag + i) % 12], "lord": SIGN_LORD[(lag + i) % 12]}
                       for i in range(12)],
            "planets": _planet_rows(c, "sidereal", lambda p: (c.sign(p) - lag) % 12 + 1)} | _common(c)


def chart_chokoisky(c: Chart):
    cusps = [c.sid_pt(x) for x in c.cusps]
    kp_cusps = [c.sid_pt(x, kp=True) for x in c.cusps]
    d1 = {"variant": "chokoisky", "zodiac": "sidereal (Lahiri; KP for sublords)", "houses_system": "Placidus",
          "ayanamsha": round(c.ay_lahiri, 5), "ayanamsha_kp": round(c.ay_kp, 5),
          "ascendant_deg": round(cusps[0], 4), "ascendant": fmt_deg(cusps[0]),
          "cusps_placidus": [{"house": i + 1, "lon": round(x, 4), "pos": fmt_deg(x), "lord": SIGN_LORD[int(x // 30)]}
                             for i, x in enumerate(cusps)],
          "sublords": [{"house": i + 1, "kp_lon": round(x, 4), "star_lord": nak_lord(x), "sub_lord": sub_lord(x)}
                       for i, x in enumerate(kp_cusps)],
          "planets": _planet_rows(c, "sidereal", lambda p: c.house_of(c.trop[p]))} | _common(c)
    asc9 = d9(cusps[0])
    d9c = {"variant": "chokoisky_d9", "ascendant_deg": round(asc9, 4), "ascendant": fmt_deg(asc9),
           "descendant": fmt_deg(asc9 + 180),
           "planets": {p: {"lon": round(d9(c.sid(p)), 4), "pos": fmt_deg(d9(c.sid(p))),
                           "sign": SIGNS[int(d9(c.sid(p)) // 30)],
                           "distance_to_asc": round(sep(d9(c.sid(p)), asc9), 3),
                           "distance_to_desc": round(sep(d9(c.sid(p)), asc9 + 180), 3)} for p in PLANET_ORDER
                       if not math.isnan(c.trop[p])}}
    return d1, d9c


def chart_frawley(c: Chart):
    pof = fortuna(c)
    resignation = norm(c.trop[SA] + c.trop[JU] - c.trop[SU])
    return {"variant": "frawley", "zodiac": "tropical", "houses_system": "Placidus",
            "ascendant_deg": round(c.asc, 4), "ascendant": fmt_deg(c.asc), "mc": fmt_deg(c.mc),
            "cusps_placidus": [{"house": i + 1, "lon": round(x, 4), "pos": fmt_deg(x),
                                "ruler": SIGN_LORD[int(x // 30)]} for i, x in enumerate(c.cusps)],
            "cusps_wholesign": [SIGNS[(int(c.asc // 30) + i) % 12] for i in range(12)],
            "planets": _planet_rows(c, "tropical", lambda p: c.house_of(c.trop[p])),
            "antiscia": {p: {"lon": round(antiscion(c.trop[p]), 4), "pos": fmt_deg(antiscion(c.trop[p]))}
                         for p in PLANET_ORDER if not math.isnan(c.trop[p])} |
                        {"Fortuna": {"lon": round(antiscion(pof), 4), "pos": fmt_deg(antiscion(pof))}},
            "part_of_fortune": {"lon": round(pof, 4), "pos": fmt_deg(pof)},
            "part_of_resignation": {"lon": round(resignation, 4), "pos": fmt_deg(resignation)}} | _common(c)


def natal_points(birth_utc: datetime | None, birth_date, lat=None, lon=None):
    """Founding chart for Rao's Nations' Charts phase: sidereal Moon sign, and the
    Ascendant sign only when a founding time and place are known."""
    if birth_utc is not None and lat is not None and lon is not None:
        jd = julday(birth_utc)
        moon, _ = _calc(jd, swe.MOON)
        asc = swe.houses_ex(jd, lat, lon, b"P")[1][0]
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ay = swe.get_ayanamsa_ut(jd)
        return {"moon_sign": int(norm(moon - ay) // 30), "asc_sign": int(norm(asc - ay) // 30)}
    dt = datetime(birth_date.year, birth_date.month, birth_date.day, 12, tzinfo=timezone.utc)
    jd = julday(dt)
    moon, _ = _calc(jd, swe.MOON)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    return {"moon_sign": int(norm(moon - swe.get_ayanamsa_ut(jd)) // 30), "asc_sign": None}
