"""Astrological (Western tropical + Vedic sidereal) and numerological features.

Everything here is computed from first principles so the tool has no
ephemeris dependency:

* Sun / Moon longitudes: Meeus low-precision series (error < ~0.5 deg).
* Planets: JPL Keplerian mean elements (Standish, valid 1800-2050), error ~1 deg,
  which is enough to get signs, elements and retrograde stations right except
  within a day or so of a boundary.
* Sidereal zodiac: Lahiri ayanamsa (linear approximation).

Features are deliberately *pre-match only*: they depend on the match date and,
optionally, on an entity "birth" date (club founding date, player DOB) and name.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from functools import lru_cache

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ELEMENTS = ["fire", "earth", "air", "water"]          # sign index % 4
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
              "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
              "Revati"]
# Vedic weekday lords Mon..Sun (Python weekday 0..6)
DAY_LORDS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
MARTIAL_DAY_LORDS = {"Mars", "Sun", "Saturn"}

# JPL approximate Keplerian elements, J2000, (value, rate per Julian century)
# a [AU], e, I [deg], L [deg], long.peri [deg], long.node [deg]
_ELEMENTS = {
    "Mercury": [(0.38709927, 0.00000037), (0.20563593, 0.00001906), (7.00497902, -0.00594749),
                (252.25032350, 149472.67411175), (77.45779628, 0.16047689), (48.33076593, -0.12534081)],
    "Venus": [(0.72333566, 0.00000390), (0.00677672, -0.00004107), (3.39467605, -0.00078890),
              (181.97909950, 58517.81538729), (131.60246718, 0.00268329), (76.67984255, -0.27769418)],
    "Earth": [(1.00000261, 0.00000562), (0.01671123, -0.00004392), (-0.00001531, -0.01294668),
              (100.46457166, 35999.37244981), (102.93768193, 0.32327364), (0.0, 0.0)],
    "Mars": [(1.52371034, 0.00001847), (0.09339410, 0.00007882), (1.84969142, -0.00813131),
             (-4.55343205, 19140.30268499), (-23.94362959, 0.44441088), (49.55953891, -0.29257343)],
    "Jupiter": [(5.20288700, -0.00011607), (0.04838624, -0.00013253), (1.30439695, -0.00183714),
                (34.39644051, 3034.74612775), (14.72847983, 0.21252668), (100.47390909, 0.20469106)],
    "Saturn": [(9.53667594, -0.00125060), (0.05386179, -0.00050991), (2.48599187, 0.00193609),
               (49.95424423, 1222.49362201), (92.59887831, -0.41897216), (113.66242448, -0.28867794)],
}


def _to_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(str(d)[:10]).date()


def julian_day(d: date, hour: float = 12.0) -> float:
    y, m = d.year, d.month
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d.day + hour / 24 + b - 1524.5


def _norm(x: float) -> float:
    return x % 360.0


def sun_longitude(jd: float) -> float:
    t = (jd - 2451545.0) / 36525
    l0 = 280.46646 + 36000.76983 * t
    m = math.radians(357.52911 + 35999.05029 * t)
    c = ((1.914602 - 0.004817 * t) * math.sin(m) + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    return _norm(l0 + c)


def moon_longitude(jd: float) -> float:
    t = (jd - 2451545.0) / 36525
    lp = 218.3164477 + 481267.88123421 * t
    d = math.radians(297.8501921 + 445267.1114034 * t)
    m = math.radians(357.5291092 + 35999.0502909 * t)
    mp = math.radians(134.9633964 + 477198.8675055 * t)
    f = math.radians(93.2720950 + 483202.0175233 * t)
    lon = (lp + 6.288774 * math.sin(mp) + 1.274027 * math.sin(2 * d - mp)
           + 0.658314 * math.sin(2 * d) + 0.213618 * math.sin(2 * mp)
           - 0.185116 * math.sin(m) - 0.114332 * math.sin(2 * f)
           + 0.058793 * math.sin(2 * d - 2 * mp) + 0.057066 * math.sin(2 * d - m - mp)
           + 0.053322 * math.sin(2 * d + mp) + 0.045758 * math.sin(2 * d - m))
    return _norm(lon)


def _helio(planet: str, t: float):
    (a, e, inc, L, wbar, node) = [v + r * t for v, r in _ELEMENTS[planet]]
    M = math.radians(_norm(L - wbar))
    E = M
    for _ in range(8):
        E = E - (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    xp, yp = a * (math.cos(E) - e), a * math.sqrt(1 - e * e) * math.sin(E)
    w, O, I = math.radians(wbar - node), math.radians(node), math.radians(inc)
    cw, sw, cO, sO, cI, sI = math.cos(w), math.sin(w), math.cos(O), math.sin(O), math.cos(I), math.sin(I)
    x = (cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp
    y = (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp
    return x, y


def planet_longitude(planet: str, jd: float) -> float:
    t = (jd - 2451545.0) / 36525
    px, py = _helio(planet, t)
    ex, ey = _helio("Earth", t)
    return _norm(math.degrees(math.atan2(py - ey, px - ex)))


def is_retrograde(planet: str, jd: float) -> bool:
    d = (planet_longitude(planet, jd + 0.5) - planet_longitude(planet, jd - 0.5) + 540) % 360 - 180
    return d < 0


def ayanamsa(jd: float) -> float:
    """Lahiri ayanamsa, linear approximation (~0.01 deg over 1950-2050)."""
    return 23.853 + (jd - 2451545.0) / 365.25 * 0.013969


# ---------------------------------------------------------------- numerology
_PYTH = {c: (i % 9) + 1 for i, c in enumerate("abcdefghijklmnopqrstuvwxyz")}


def reduce_num(n: int, keep_master: bool = False) -> int:
    while n > 9:
        if keep_master and n in (11, 22, 33):
            return n
        n = sum(int(c) for c in str(n))
    return n


def name_number(name: str) -> int:
    import unicodedata
    s = unicodedata.normalize("NFKD", name.lower())
    total = sum(_PYTH.get(c, 0) for c in s)
    return reduce_num(total) if total else 0


def universal_day(d: date) -> int:
    return reduce_num(sum(int(c) for c in d.strftime("%Y%m%d")))


def life_path(d: date) -> int:
    return reduce_num(reduce_num(d.year) + reduce_num(d.month) + reduce_num(d.day))


def personal_day(birth: date, d: date) -> int:
    return reduce_num(reduce_num(birth.month) + reduce_num(birth.day) + universal_day(d))


# Classic numerology "friendly" number pairs (Cheiro-style planetary friendships)
_FRIENDLY = {1: {1, 2, 3, 9}, 2: {1, 2, 7}, 3: {1, 3, 6, 9}, 4: {1, 4, 6, 8},
             5: {1, 5, 6}, 6: {3, 5, 6, 9}, 7: {2, 7}, 8: {4, 6, 8}, 9: {1, 3, 6, 9}}


def num_harmony(a: int, b: int) -> float:
    if a == 0 or b == 0:
        return 0.0
    return 1.0 if b in _FRIENDLY.get(a, set()) else -1.0


# ---------------------------------------------------------------- sky state
@lru_cache(maxsize=200_000)
def sky(d) -> dict:
    """Sky state at local noon of date `d` (both zodiacs)."""
    d = _to_date(d)
    jd = julian_day(d)
    sun, moon = sun_longitude(jd), moon_longitude(jd)
    ay = ayanamsa(jd)
    elong = _norm(moon - sun)
    moon_sid = _norm(moon - ay)
    mars = planet_longitude("Mars", jd)
    return {
        "jd": jd,
        "sun_trop": sun, "moon_trop": moon,
        "sun_sign": int(sun // 30), "moon_sign": int(moon // 30),
        "moon_sign_sid": int(moon_sid // 30), "sun_sign_sid": int(_norm(sun - ay) // 30),
        "elongation": elong,
        "tithi": int(elong // 12) + 1,                      # 1..30
        "nakshatra": int(moon_sid // (360 / 27)),           # 0..26
        "mars_sign": int(mars // 30),
        "mercury_rx": is_retrograde("Mercury", jd),
        "mars_rx": is_retrograde("Mars", jd),
        "venus_rx": is_retrograde("Venus", jd),
        "day_lord": DAY_LORDS[d.weekday()],
        "universal_day": universal_day(d),
    }


@lru_cache(maxsize=50_000)
def natal(birth) -> dict:
    birth = _to_date(birth)
    s = sky(birth)
    return {"sun_sign": s["sun_sign"], "moon_sign": s["moon_sign"],
            "nakshatra": s["nakshatra"], "moon_sign_sid": s["moon_sign_sid"],
            "life_path": life_path(birth), "birth": birth}


def _element_harmony(sign_a: int, sign_b: int) -> float:
    """Traditional aspect quality between two signs: trine/sextile/conjunct +, square/opposition -."""
    k = (sign_b - sign_a) % 12
    return {0: 1.0, 2: 0.5, 4: 1.0, 8: 1.0, 10: 0.5, 3: -1.0, 9: -1.0, 6: -0.5}.get(k, 0.0)


def tara_bala(birth_nak: int, transit_nak: int) -> float:
    """Vedic Tara Bala: count from birth nakshatra to transit nakshatra, mod 9.
    Taras 3 (Vipat), 5 (Pratyak), 7 (Naidhana) are inauspicious; others auspicious."""
    tara = ((transit_nak - birth_nak) % 27) % 9 + 1
    return -1.0 if tara in (3, 5, 7) else (0.0 if tara == 1 else 1.0)


def chandra_bala(birth_moon_sid: int, transit_moon_sid: int) -> float:
    """Vedic Chandra Bala: transit Moon in houses 1,3,6,7,10,11 from natal Moon is favourable."""
    house = (transit_moon_sid - birth_moon_sid) % 12 + 1
    return 1.0 if house in (1, 3, 6, 7, 10, 11) else -1.0


def entity_score(name: str, birth, d) -> dict:
    """Esoteric 'strength' of one competitor on match date d."""
    s = sky(d)
    nn = name_number(name)
    out = {
        "name_num_harmony": num_harmony(nn, s["universal_day"]),
        "name_num_match": 1.0 if nn == s["universal_day"] else 0.0,
    }
    if birth is not None:
        n = natal(birth)
        out.update({
            "sun_transit_harmony": _element_harmony(n["sun_sign"], s["sun_sign"]),
            "moon_transit_harmony": _element_harmony(n["sun_sign"], s["moon_sign"]),
            "mars_transit_harmony": _element_harmony(n["sun_sign"], s["mars_sign"]),
            "tara_bala": tara_bala(n["nakshatra"], s["nakshatra"]),
            "chandra_bala": chandra_bala(n["moon_sign_sid"], s["moon_sign_sid"]),
            "personal_day_harmony": num_harmony(personal_day(n["birth"], _to_date(d)), n["life_path"]),
            "lifepath_day_match": 1.0 if n["life_path"] == s["universal_day"] else 0.0,
        })
    return out


def match_features(home: str, away: str, d, home_birth=None, away_birth=None) -> dict:
    """Esoteric feature vector for a match. Entity features are home-minus-away
    differences; date-level features describe the sky itself."""
    s = sky(d)
    f = {
        "moon_phase_sin": math.sin(math.radians(s["elongation"])),
        "moon_phase_cos": math.cos(math.radians(s["elongation"])),
        "moon_fire_air": 1.0 if s["moon_sign"] % 2 == 0 else -1.0,   # masculine/active signs
        "tithi_rikta": 1.0 if s["tithi"] % 15 in (4, 9, 14) else 0.0,  # Rikta (empty) tithis
        "mercury_rx": float(s["mercury_rx"]),
        "mars_rx": float(s["mars_rx"]),
        "martial_day_lord": 1.0 if s["day_lord"] in MARTIAL_DAY_LORDS else 0.0,
    }
    h, a = entity_score(home, home_birth, d), entity_score(away, away_birth, d)
    for k in set(h) | set(a):
        f["diff_" + k] = h.get(k, 0.0) - a.get(k, 0.0)
        f["sum_" + k] = h.get(k, 0.0) + a.get(k, 0.0)   # joint 'energy' of both sides (for totals)
    return f


def describe_sky(d) -> str:
    s = sky(d)
    return (f"Sun {SIGNS[s['sun_sign']]} (trop) / {SIGNS[s['sun_sign_sid']]} (sid); "
            f"Moon {SIGNS[s['moon_sign']]} (trop) / {SIGNS[s['moon_sign_sid']]} (sid), "
            f"nakshatra {NAKSHATRAS[s['nakshatra']]}, tithi {s['tithi']}; "
            f"Mercury {'Rx' if s['mercury_rx'] else 'direct'}, Mars {'Rx' if s['mars_rx'] else 'direct'}; "
            f"day lord {s['day_lord']}; universal day {s['universal_day']}")
