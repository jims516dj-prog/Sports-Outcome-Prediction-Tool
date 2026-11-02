"""Three classical sports-astrology engines, computed from kickoff time + venue.

  * Rao       - "Sports Astrology: The Inclusive Methodology" (Vedic, Lahiri, whole-sign)
  * Chokoisky - "Gambler's Dharma" (Vedic, Lahiri + KP sublords, Placidus, D1 + D9)
  * Frawley   - "Sports Astrology" event-chart method (tropical, Placidus)

Implemented from the build specification supplied by the user. Every engine works
from the FAVOURITE's point of view (favourite = 1st house / Lagna, underdog = 7th)
and returns a signed score (+ = favourite) and a verdict in {"fav", "und", "draw"}.

Where the specification cites book tables that were not available here, the
standard classical tables are used (documented next to each table):
Parashari natural friendships (Rao p.39), Avakahada-chakra pada syllables
(Chokoisky table 7.1), classical dignities (Chokoisky table 3.1).

Requires pyswisseph (`pip install pyswisseph`).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import swisseph as swe

EPHE = os.environ.get("SE_EPHE_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "ephe"))
swe.set_ephe_path(EPHE)

SU, MO, MA, ME, JU, VE, SA, RA, KE, UR, NE, PL, CH, CE, UK, GU = (
    "Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke", "Ur", "Ne", "Pl", "Ch", "Ce", "Uk", "Gu")
_SWE_ID = {SU: swe.SUN, MO: swe.MOON, MA: swe.MARS, ME: swe.MERCURY, JU: swe.JUPITER,
           VE: swe.VENUS, SA: swe.SATURN, UR: swe.URANUS, NE: swe.NEPTUNE, PL: swe.PLUTO,
           CH: swe.CHIRON, CE: swe.CERES}
GRAHAS = [SU, MO, MA, ME, JU, VE, SA, RA, KE]
INVISIBLE = {RA, KE, UR, NE, PL, CE, CH, UK, GU}
MALEFICS = {SU, MA, SA, RA, KE}
BENEFICS = {JU, VE, ME, MO}

# sign index 0=Aries .. 11=Pisces ; traditional rulers (used by all three engines)
SIGN_LORD = [MA, VE, ME, MO, SU, ME, VE, MA, JU, SA, SA, JU]
EXALT = {SU: 0, MO: 1, MA: 9, ME: 5, JU: 3, VE: 11, SA: 6, RA: 1, KE: 7}
DEBIL = {p: (s + 6) % 12 for p, s in EXALT.items()}
OWN = {SU: {4}, MO: {3}, MA: {0, 7}, ME: {2, 5}, JU: {8, 11}, VE: {1, 6}, SA: {9, 10}}
DIG_BALA_HOUSE = {JU: 1, ME: 1, SU: 10, MA: 10, SA: 7, MO: 4, VE: 4}
# Vimshottari order (nakshatra lords) and years
VIM = [KE, VE, SU, MO, MA, RA, JU, SA, ME]
VIM_YEARS = {KE: 7, VE: 20, SU: 6, MO: 10, MA: 7, RA: 18, JU: 16, SA: 19, ME: 17}

# Parashari natural friendships (standard table; stands in for Rao p.39)
FRIENDS = {SU: {MO, MA, JU}, MO: {SU, ME}, MA: {SU, MO, JU}, ME: {SU, VE}, JU: {SU, MO, MA},
           VE: {ME, SA}, SA: {ME, VE}, RA: {ME, VE, SA}, KE: {MA, JU}}
ENEMIES = {SU: {VE, SA}, MO: set(), MA: {ME}, ME: {MO}, JU: {ME, VE}, VE: {SU, MO},
           SA: {SU, MO, MA}, RA: {SU, MO, MA}, KE: {SU, MO}}

# 108 nakshatra-pada syllables (Avakahada chakra; stands in for Chokoisky table 7.1)
PADA_SYLLABLES = (
    "chu che cho la  li lu le lo  a i u e  o va vi vu  ve vo ka ki  ku gha nga chha  "
    "ke ko ha hi  hu he ho da  di du de do  ma mi mu me  mo ta ti tu  te to pa pi  "
    "pu sha na tha  pe po ra ri  ru re ro ta  ti tu te to  na ni nu ne  no ya yi yu  "
    "ye yo ba bi  bu dha pha dha  be bo ja ji  ju je jo gha  ga gi gu ge  go sa si su  "
    "se so da di  du tha jha na  de do cha chi").split()
assert len(PADA_SYLLABLES) == 108

# Yogataras, sidereal (Lahiri) longitudes from the specification, with effects
STARS = {"Regulus": (126.0, 7), "Pollux": (89.5, 7), "Vega": (261.5, 7), "Spica": (179.92, -7),
         "Antares": (226.0, 0), "Algol": (56.0, -4), "Wasat": (85.0, -4), "Hyades": (42.0, 3)}

# Chokoisky table 4.1 (D1 cusps): effect on (1/7, 4/10, 6/12) axes; "M" = Mercury rule, "UR"/"NE" = by motion
D1_EFFECT = {SU: (-1, -1, -1), MO: (-1, -1, -1), MA: (1, -1, 1), RA: (1, 1, 1), JU: (1, 1, 1),
             SA: (-1, 1, 1), ME: ("M", "M", 1), KE: (-1, -1, -1), VE: (1, 1, 1), UR: ("UR",) * 3,
             NE: ("NE",) * 3, PL: (-1, 1, -1), UK: (-1, -1, -1), GU: (-1, 1, 0), CH: (0, 0, 0), CE: (0, 0, 0)}
# Chokoisky table 5.3 (D9 1/7 cusps) - Mars, Mercury, Venus reversed vs D1
D9_EFFECT = {SU: -1, MO: -1, MA: -1, RA: 1, JU: 1, SA: -1, ME: 1, KE: -1, VE: -1, UR: "UR", NE: "NE",
             PL: -1, UK: -1, GU: -1, CH: 0, CE: 0}
BRIGHTNESS = [VE, JU, MA, ME, SA]   # planetary war: brighter (earlier) wins


def norm(x):
    return x % 360.0


def sep(a, b):
    """Smallest angular separation."""
    d = abs(norm(a) - norm(b)) % 360
    return min(d, 360 - d)


def signed(a, b):
    """b - a in (-180, 180]."""
    return (b - a + 180) % 360 - 180


# ------------------------------------------------------------------ chart
@dataclass
class Chart:
    jd: float
    lat: float
    lon: float
    trop: dict = field(default_factory=dict)      # planet -> tropical longitude
    speed: dict = field(default_factory=dict)
    cusps: list = field(default_factory=list)     # Placidus, tropical, index 0 = 1st
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

    def sign(self, p):                 # sidereal sign
        return int(self.sid(p) // 30)

    def trop_sign(self, x):
        return int(norm(x) // 30)

    def house_of(self, x):             # Placidus house (1..12) of a tropical longitude
        for i in range(12):
            a, b = self.cusps[i], self.cusps[(i + 1) % 12]
            if norm(x - a) < norm(b - a):
                return i + 1
        return 12

    def retro(self, p):
        return self.speed.get(p, 1) < 0


def _calc(jd, pid, flags=swe.FLG_SWIEPH | swe.FLG_SPEED):
    try:
        r = swe.calc_ut(jd, pid, flags)[0]
    except swe.Error:
        r = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)[0]
    return r[0], r[3]


def _asc_at(jd, lat, lon):
    return swe.houses_ex(jd, lat, lon, b"P")[1][0]


def compute_chart(dt_utc: datetime, lat: float, lon: float) -> Chart:
    h = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    jd = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, h)
    c = Chart(jd, lat, lon)
    for p, pid in _SWE_ID.items():
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
    c.trop[UK] = norm(c.trop[SU] - 30)            # Upaketu = Sun - 30 deg
    c.trop[GU], c.sunrise, c.sunset = _gulika(c, dt_utc)
    c.speed[UK] = c.speed[GU] = 1.0
    return c


def _rise_set(jd0, lat, lon, rsmi):
    try:
        res, t = swe.rise_trans(jd0, swe.SUN, rsmi, (lon, lat, 0.0))
        return t[0] if res == 0 else None
    except Exception:
        return None


def _gulika(c: Chart, dt_utc):
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
    order = [SU, MO, MA, ME, JU, VE, SA]
    # weekday of the local sunrise date (0 = Sunday)
    vedic_day = (int(math.floor(rise + 0.5 + c.lon / 360)) + 1) % 7   # 0 = Sunday
    lord = order[vedic_day]
    if jd < sset:
        start, length, first = rise, (sset - rise) / 8, order.index(lord)
    else:
        start, length, first = sset, (nrise - sset) / 8, (order.index(lord) + 4) % 7
    k = next(i for i in range(7) if (first + i) % 7 == 6)        # Saturn's portion
    return _asc_at(start + k * length, c.lat, c.lon), rise, sset


# ------------------------------------------------------------------ helpers
def dignity(p, sign):
    if p in EXALT and EXALT[p] == sign:
        return 2
    if p in OWN and sign in OWN[p]:
        return 1
    if p in DEBIL and DEBIL[p] == sign:
        return -1
    return 0


def nak_lord(sid_lon):
    return VIM[int(sid_lon // (360 / 27)) % 9]


def sub_lord(sid_lon):
    nak_len = 360 / 27
    start_lord = VIM.index(nak_lord(sid_lon))
    pos = (sid_lon % nak_len) / nak_len * 120
    acc = 0.0
    for i in range(9):
        p = VIM[(start_lord + i) % 9]
        acc += VIM_YEARS[p]
        if pos < acc:
            return p
    return VIM[(start_lord + 8) % 9]


def relation(a, b):
    if a not in FRIENDS or b not in FRIENDS:
        return 0
    return 1 if b in FRIENDS[a] else (-1 if b in ENEMIES[a] else 0)


def vedic_aspects(p, from_sign):
    """Signs aspected by planet p sitting in from_sign (whole-sign graha drishti)."""
    extra = {MA: [4, 8], JU: [5, 9], SA: [3, 10], RA: [5, 9], KE: [5, 9]}.get(p, [])
    return {(from_sign + k - 1) % 12 for k in [7] + extra}


def moon_waxing(c):
    return norm(c.trop[MO] - c.trop[SU]) < 180


# ================================================================== RAO
def rao(c: Chart, nation_fav=None, nation_und=None):
    """Rao's Game Analysis (+ optional Nations' Charts). nation_* = natal sidereal
    Moon sign index (0-11) of the team's founding chart, if known."""
    sign_of = {p: c.sign(p) for p in GRAHAS}
    lagna = int(c.sid_pt(c.asc) // 30)

    def quality(p):
        benefic = p in BENEFICS and not (p == MO and not moon_waxing(c))
        q = 1.0 if benefic else -1.0
        d = dignity(p, sign_of[p])
        if d >= 1:
            q *= 1.5 if q > 0 else 0.5      # dignified malefic does less harm
        elif d < 0:
            q = q * 0.5 if q > 0 else q * 1.5
        return q

    def influence(sign, exclude=()):
        net, n = 0.0, 0
        lord = SIGN_LORD[sign]
        for p in GRAHAS:
            if p in exclude:
                continue
            w = 1.0 if sign_of[p] == sign else (0.75 if sign in vedic_aspects(p, sign_of[p]) else 0)
            if w:
                net += w * (quality(p) + 0.5 * relation(p, lord))
                n += 1
        return net, n

    def to_points(net):
        if net <= -0.5:
            return 0
        if net < 0.5:
            return 1
        return 2 if net < 2 else 3

    def house_points(sign):
        net, _ = influence(sign)
        lord = SIGN_LORD[sign]
        net += 0.5 * max(-1, min(1, dignity(lord, sign_of[lord])))
        return to_points(net)

    def team(l):
        H = lambda n: (l + n - 1) % 12
        lord = SIGN_LORD[l]
        h_from = (sign_of[lord] - l) % 12 + 1
        lnet, _ = influence(sign_of[lord], exclude=(lord,))
        lnet += {1: 1, 4: 1, 5: 1, 9: 1, 10: 1, 11: 0.5, 6: -1, 8: -1, 12: -1}.get(h_from, 0)
        lnet += max(-1, min(1, dignity(lord, sign_of[lord])))
        pts = {"ascendant": house_points(H(1)), "asc_lord": to_points(lnet),
               "score": house_points(H(10)),
               "game_coach": round((house_points(H(5)) + house_points(H(3))) / 2, 1),
               "fans_odds": house_points(H(2)), "penalties": house_points(H(12))}
        return pts

    fav, und = team(lagna), team((lagna + 6) % 12)
    caveats = ["Planetary-influence layer skipped (no captain/jersey data)"]
    for key, nat, l in (("nation_moon_fav", nation_fav, lagna), ("nation_moon_und", nation_und, (lagna + 6) % 12)):
        if nat is None:
            continue
        net, _ = influence(nat)
        h = (nat - l) % 12 + 1
        net += 0.5 if h in (1, 3, 6, 10, 11) else (-0.5 if h in (6, 8, 12) else 0)
        (fav if key.endswith("fav") else und)["nation_moon"] = to_points(net)
        if (nat + 7) % 12 in vedic_aspects(SA, sign_of[SA]) or sign_of[SA] == (nat + 7) % 12:
            caveats.append("Saturn on 8th from nation Moon - interruption risk")
    diff = sum(fav.values()) - sum(und.values())
    return {"fav": fav, "und": und, "diff": diff,
            "verdict": "fav" if diff > 0 else ("und" if diff < 0 else "draw"),
            "caveats": caveats, "saturn_8th": any("Saturn" in x for x in caveats)}


# ================================================================== CHOKOISKY
FAV_HOUSES, UND_HOUSES = {1, 3, 6, 10, 11}, {7, 9, 12, 4, 5}


def chokoisky(c: Chart, fav_name="", und_name=""):
    rows = {}
    house = {p: c.house_of(c.trop[p]) for p in c.trop if p != "TrueNode"}
    sid_sign = {p: int(c.sid(p) // 30) for p in GRAHAS}
    elong = norm(c.trop[MO] - c.trop[SU])

    def exaggerated(p):
        s = sid_sign[p]
        return (dignity(p, s) >= 1 or c.retro(p) or nak_lord(c.sid(p)) == p
                or DIG_BALA_HOUSE.get(p) == house[p] or (p == MO and abs(elong - 180) < 12))

    # 1. Victory houses
    vh = 0.0
    for p in GRAHAS:
        if p in (RA, KE) or p in MALEFICS:
            d = dignity(p, sid_sign[p]) if p in EXALT else 0
            pts = 2.0 if d < 0 else (3.0 if (d >= 1 or DIG_BALA_HOUSE.get(p) == house[p]) else 2.5)
        elif p in BENEFICS and dignity(p, sid_sign[p]) < 0:
            pts = 2.0
        elif p in BENEFICS and exaggerated(p):
            pts = 2.5
        else:
            continue
        vh += pts if house[p] in FAV_HOUSES else (-pts if house[p] in UND_HOUSES else 0)
    rows["victory_houses"] = vh

    # 2. SKY / PKY around 1st and 7th
    def hemmed(h):
        before, after = (h - 2) % 12 + 1, h % 12 + 1
        side = lambda hh: {p for p in GRAHAS if house[p] == hh}
        a, b = side(before), side(after)
        if not a or not b:
            # a lone node on one side gives a half effect
            return 0.0
        ben = lambda s: s and all(p in BENEFICS for p in s)
        mal = lambda s: s and all(p in MALEFICS for p in s)
        if ben(a) and ben(b):
            return 8.0
        if (ben(a) and b <= {SU, KE}) or (ben(b) and a <= {SU, KE}):
            return 3.5
        if mal(a) and mal(b):
            return -7.0
        return 0.0
    rows["sky_pky"] = hemmed(1) - hemmed(7)

    # 3. D1 cuspal strength
    cusp_team = {1: (1, 0), 7: (-1, 0), 10: (1, 1), 4: (-1, 1), 6: (1, 2), 12: (-1, 2)}
    sid_cusp_sign = lambda i: int(c.sid_pt(c.cusps[i - 1]) // 30)
    fav_lorded = {SIGN_LORD[sid_cusp_sign(h)] for h in FAV_HOUSES}
    und_lorded = {SIGN_LORD[sid_cusp_sign(h)] for h in UND_HOUSES}

    def eff(e, p, team_sign):
        if e == "M":
            return 1 if (p == ME and (ME in (fav_lorded if team_sign > 0 else und_lorded))) else -1
        if e == "UR":
            return -1 if c.retro(UR) else 1
        if e == "NE":
            return 1 if c.retro(NE) else -1
        return e

    d1 = 0.0
    for h, (team_sign, axis) in cusp_team.items():
        for p in D1_EFFECT:
            orb = (2.0 if p in INVISIBLE else 2.5) + (0.5 if (c.retro(p) or (p in EXALT and EXALT[p] == sid_sign.get(p))) else 0)
            if sep(c.trop[p], c.cusps[h - 1]) <= orb:
                d1 += team_sign * eff(D1_EFFECT[p][axis], p, team_sign) * (7 if p in INVISIBLE else 8)
    rows["d1_cusps"] = d1

    # 4. Navamsha (D9) cuspal strength
    d9 = lambda x: norm(x * 9)
    d9_asc = d9(c.sid_pt(c.asc))
    d9v, d9_present = 0.0, False
    for p in D9_EFFECT:
        pl = d9(c.sid(p))
        orb = 2.0 if p in INVISIBLE else 2.5
        for team_sign, cusp in ((1, d9_asc), (-1, norm(d9_asc + 180))):
            if sep(pl, cusp) <= orb:
                e = eff(D9_EFFECT[p], p, team_sign)
                d9v += team_sign * e * (13.5 if p in INVISIBLE else 16)
                d9_present = d9_present or e != 0
    rows["d9_cusps"] = d9v

    # 5. Nama pada - MC navamsha syllable vs team names
    syl = PADA_SYLLABLES[int(c.sid_pt(c.mc) // (360 / 108)) % 108]
    np_f, np_u = name_matches(syl, fav_name), name_matches(syl, und_name)
    rows["nama_pada"] = 16.0 * (np_f - np_u)

    # 6. KP sublords of cusps 1 and 7
    kp_cusp_sign = lambda i: int(c.sid_pt(c.cusps[i - 1], kp=True) // 30)
    owned = {p: [i for i in range(1, 13) if SIGN_LORD[kp_cusp_sign(i)] == p] for p in GRAHAS}
    for node in (RA, KE):
        owned[node] = owned[SIGN_LORD[int(c.sid(node, kp=True) // 30)]]

    def house_factor(h):
        return 1 if h in FAV_HOUSES else (0.5 if h == 2 else (-1 if (h in UND_HOUSES or h == 8) else 0))

    def kp_score(p):
        star = nak_lord(c.sid(p, kp=True))
        s = 4 * house_factor(house[star]) + 3 * house_factor(house[p])
        s += 2 * sum(house_factor(h) for h in owned[star]) + sum(house_factor(h) for h in owned[p])
        return s
    sl1 = sub_lord(c.sid_pt(c.cusps[0], kp=True))
    sl7 = sub_lord(c.sid_pt(c.cusps[6], kp=True))
    sub_diff = kp_score(sl1) + kp_score(sl7)
    rows["sublords"] = 8 * math.tanh(sub_diff / 8)

    # 7. Nakshatra taras on cusps 1/10 (fav), 7/4 (und) and their lords
    tara = 0.0
    for team_sign, hs in ((1, (1, 10)), (-1, (7, 4))):
        pts = [c.sid_pt(c.cusps[h - 1]) for h in hs] + [c.sid(SIGN_LORD[sid_cusp_sign(h)]) for h in hs]
        for x in pts:
            for _, (pos, e) in STARS.items():
                if sep(x, pos) <= 1.0:
                    tara += team_sign * e
    rows["nakshatra_tara"] = tara

    # 8. Planetary war among lords of 1/10 (fav) and 7/4 (und)
    fav_l = {SIGN_LORD[sid_cusp_sign(h)] for h in (1, 10)}
    und_l = {SIGN_LORD[sid_cusp_sign(h)] for h in (7, 4)}
    war = 0.0
    for i, a in enumerate(BRIGHTNESS):
        for b in BRIGHTNESS[i + 1:]:
            if sep(c.trop[a], c.trop[b]) <= 1.0:          # a is brighter -> wins
                war += 5 * ((a in fav_l) - (a in und_l)) - 5 * ((b in fav_l) - (b in und_l))
    rows["planetary_war"] = war

    total = sum(rows.values())
    verdict = "fav" if total > 3 else ("und" if total < -3 else "draw")
    conf = "high" if abs(total) > 9 else ("medium" if abs(total) >= 5 else "low")
    return {"rows": rows, "total": total, "verdict": verdict, "goal_diff": round(abs(total) / 3),
            "confidence": conf, "d9_cusp_planet": d9_present, "sky": hemmed(1) > 0 or hemmed(7) > 0,
            "sublord_diff": sub_diff, "nama_pada_fav": np_f, "nama_pada_und": np_u, "mc_syllable": syl}


_SKIP_WORDS = {"fc", "afc", "cf", "ac", "as", "ss", "ssc", "us", "sc", "sv", "vfl", "vfb", "tsg", "rc", "rcd",
               "cd", "ud", "sd", "ca", "club", "de", "real", "1.", "fsv", "bor.", "borussia", "spvgg", "acf",
               "ogc", "osc", "losc", "hsc", "sm", "aj", "fco", "estac", "ea", "calcio", "olympique", "stade",
               "racing", "athletic", "atlético", "deportivo", "sporting", "hellas", "bayer", "eintracht",
               "fortuna", "1899", "hertha", "werder", "holstein", "arminia", "paris", "saint", "the"}


def _translit(word):
    import unicodedata
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(ch for ch in w if ch.isalpha()).replace("ch", "#")
    for a, b in (("w", "v"), ("f", "ph"), ("z", "jh"), ("q", "k"), ("c", "k"), ("x", "ks"), ("y", "i")):
        w = w.replace(a, b)
    return w.replace("#", "ch")


def name_matches(syl, name):
    """Does the team's leading syllable match the pada syllable? (diphthong + substitution rules)"""
    if not name:
        return 0
    words = [w for w in name.split() if w.lower() not in _SKIP_WORDS and not w.isdigit()]
    if not words:
        return 0
    w = _translit(words[0])
    s = syl
    variants = {s}
    if s.endswith("e"):
        variants.add(s[:-1] + "ai")
    if s.endswith("o"):
        variants.add(s[:-1] + "au")
    if s.startswith("ph"):
        variants.add("p" + s[2:])
    if s.startswith("p"):
        variants.add("ph" + s[1:])
    return int(any(w.startswith(v) for v in variants))


# ================================================================== FRAWLEY
ASPECTS = {0: "conj", 60: "sextile", 90: "square", 120: "trine", 180: "opp"}


def antiscion(x):
    return norm(180 - x)


def frawley(c: Chart, extra_time=False):
    t = c.trop
    cusp = {h: c.cusps[h - 1] for h in (1, 2, 4, 7, 10)}
    lord = {h: SIGN_LORD[c.trop_sign(cusp[h])] for h in (1, 4, 7, 10)}
    team_of_lord = {}
    for h, p in lord.items():
        team_of_lord.setdefault(p, set()).add("fav" if h in (1, 10) else "und")
    T = []                                         # (team, strength, text)

    def place(x, h):
        """'on' = within 3 deg before cusp, same sign; 'in' = within 3 deg after, same sign."""
        if c.trop_sign(x) != c.trop_sign(cusp[h]):
            return None
        d = signed(cusp[h], x)
        return "on" if -3 <= d < 0 else ("in" if 0 <= d <= 3 else None)

    TABLE = {(1, 7, "on"): ("fav", 3), (1, 7, "in"): ("und", 3), (7, 1, "on"): ("und", 3),
             (7, 1, "in"): ("fav", 3), (10, 7, "on"): ("fav", 2), (10, 7, "in"): ("und", 2),
             (7, 10, "on"): ("und", 2), (7, 10, "in"): ("fav", 2), (1, 1, "on"): ("fav", 1),
             (1, 1, "in"): ("fav", 1), (4, 4, "on"): ("und", 1), (4, 4, "in"): ("und", 1),
             (10, 10, "on"): ("fav", 1), (10, 10, "in"): ("fav", 1)}
    for (lh, ch, mode), (team, s) in TABLE.items():
        p = lord[lh]
        for label, x, w in (("body", t[p], s), ("antiscion", antiscion(t[p]), s)):
            if place(x, ch) == mode:
                if c.retro(p) and mode == "in" and ch != lh:
                    continue                                  # retrograde inside enemy house: no benefit
                ww = w * (0.5 if (c.retro(p) and mode == "on" and ch != lh) else 1)
                T.append((team, ww, f"L{lh} ({p}) {label} {mode} {ch}th cusp"))

    # Moon placement
    for x, label in ((t[MO], "Moon"), (antiscion(t[MO]), "Moon antiscion")):
        for h, team in ((1, "fav"), (10, "fav"), (7, "und"), (4, "und")):
            if place(x, h):
                T.append((team, 1.5, f"{label} at {h}th cusp"))

    # Part of Fortune (antiscion only)
    pof = norm(c.asc + t[MO] - t[SU])
    apof = antiscion(pof)
    for h, team in ((1, "fav"), (7, "fav"), (10, "fav"), (4, "und")):
        if sep(apof, cusp[h]) <= 3:
            T.append((team, 3, f"Antiscion of Fortuna near {h}th cusp"))
    if sep(pof, t[SU]) <= 2:
        T.append(("und", 1, "Fortuna combust"))

    # Moon's applying aspects within range, not leaving its sign
    rng = 6.0 if extra_time else 5.0
    to_sign_end = 30 - (t[MO] % 30)
    events = []
    targets = [(p, f"L{h}", "fav" if h in (1, 10) else "und") for h, p in lord.items() if p != MO]
    for p, lab, team in targets:
        rel = c.speed[MO] - c.speed.get(p, 0)
        if rel <= 0:
            continue
        for ang in ASPECTS:
            for sgn in (1, -1):
                target = norm(t[p] + sgn * ang)
                gap = norm(target - t[MO])                      # Moon must close this gap
                travel = gap * c.speed[MO] / rel
                if 0 < travel <= min(rng, to_sign_end):
                    events.append((travel, ASPECTS[ang], lab, team, p))
    for pt, lab in ((pof, "Fortuna"), (apof, "antiscion of Fortuna")):
        for ang in ASPECTS:
            for sgn in (1, -1):
                gap = norm(norm(pt + sgn * ang) - t[MO])
                if 0 < gap <= min(rng, to_sign_end):
                    events.append((gap, ASPECTS[ang], lab, "fortuna", None))
    events.sort()
    last, late = None, False
    for travel, asp, lab, team, p in events:
        if team == "fortuna":
            winner = "fav" if asp in ("conj", "trine", "sextile") else "und"
            T.append((winner, 3, f"Moon {asp} {lab} (final)"))
            last, late = None, travel > 0.7 * rng
            break
        last, late = (team, asp, lab, p), travel > 0.7 * rng
        if asp == "conj":
            break                                               # bodily conjunctions are final
    if last:
        T.append((last[0], 3, f"Moon's last aspect: {last[1]} {last[2]} ({last[3]})"))

    # Lords to Fortuna
    for p, lab, team in ((lord[1], "L1", "fav"), (lord[7], "L7", "und")):
        for pt, plab in ((pof, "Fortuna"), (apof, "antiscion of Fortuna")):
            d = sep(t[p], pt)
            if d <= 3:
                T.append((team, 2, f"{lab} conjunct {plab}"))
            elif abs(d - 180) <= 3:
                w = team if (lab == "L7" and plab == "Fortuna") else ("und" if lab == "L1" else "fav")
                T.append((w, 2, f"{lab} opposite {plab}"))

    # Dispositor of Fortuna
    disp = SIGN_LORD[c.trop_sign(pof)]
    if disp not in (lord[1], lord[7], MO) and c.speed.get(disp, 0) != 0:
        g = signed(t[disp], pof)
        if 0 < g * (1 if c.speed[disp] > 0 else -1) <= 3:
            T.append(("fav", 1.5, f"Dispositor {disp} applying to conjunct Fortuna"))
        g2 = signed(t[disp], norm(pof + 180))
        if 0 < g2 * (1 if c.speed[disp] > 0 else -1) <= 3:
            T.append(("und", 1.5, f"Dispositor {disp} applying to oppose Fortuna"))

    # Miscellaneous
    nn, sn = t["TrueNode"], norm(t["TrueNode"] + 180)
    for p, teams in team_of_lord.items():
        for team in teams:
            other = "und" if team == "fav" else "fav"
            if sep(t[p], nn) <= 3:
                T.append((team, 1, f"North Node on {p}"))
            if sep(t[p], sn) <= 3:
                T.append((other, 1, f"South Node on {p}"))
            if p != SU and 17 / 60 < sep(t[p], t[SU]) <= 2:
                T.append((other, 1.5, f"{p} combust"))
            if SA not in (lord[1], lord[7]) and p != SA and sep(t[p], t[SA]) <= 3:
                T.append((other, 1, f"Saturn afflicts {p}"))
    if place(t[PL], 1) or sep(t[PL], cusp[1]) <= 3:
        T.append(("und", 2, "Pluto on 1st cusp"))
    if any(sep(t[PL], x) <= 3 or abs(sep(t[PL], x) - 180) <= 3 for x in (pof, apof)):
        T.append(("und", 1.5, "Pluto conjunct/opposite Fortuna"))
    if place(t[PL], 2):
        T.append(("und", 0.5, "Pluto on 2nd cusp"))
    g = signed(t[UR], c.mc)
    if 0 < g * (1 if c.speed[UR] > 0 else -1) <= 3:
        T.append(("fav", 2, "Uranus applying to MC"))
    if sep(t[UR], pof) <= 3:
        T.append(("fav", 1.5, "Uranus conjunct Fortuna"))
    if abs(sep(t[UR], pof) - 180) <= 3:
        T.append(("und", 1.5, "Uranus opposite Fortuna"))

    score = sum(w if tm == "fav" else -w for tm, w, _ in T)
    if not T:
        verdict = "fav"                                         # default rule
    else:
        verdict = "fav" if score > 0.5 else ("und" if score < -0.5 else "draw")
    n_win = sum(1 for tm, _, _ in T if tm == verdict)
    return {"testimonies": T, "score": score, "verdict": verdict, "n_testimonies": len(T),
            "goals_winner": min(4, 1 + n_win // 2), "late_goal": late,
            "lord1_on_7th": any("L1" in x and "on 7th" in x for _, _, x in T),
            "pluto_on_1st": any("Pluto on 1st" in x for _, _, x in T)}


# ================================================================== sandhi
@lru_cache(maxsize=None)
def _eclipses(y0=1990, y1=2030):
    out, jd = [], swe.julday(y0, 1, 1, 0)
    end = swe.julday(y1, 1, 1, 0)
    while jd < end:
        t = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH)[1][0]
        out.append(t)
        jd = t + 20
    jd = swe.julday(y0, 1, 1, 0)
    while jd < end:
        t = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH)[1][0]
        out.append(t)
        jd = t + 20
    return tuple(sorted(out))


def sandhi(c: Chart):
    flags = {}
    flags["eclipse_window"] = any(abs(c.jd - e) <= 3 for e in _eclipses())
    flags["sankranti"] = c.sid(SU) % 30 >= 29
    flags["sunrise_sunset"] = any(x is not None and abs(c.jd - x) * 1440 <= 30 for x in (c.sunrise, c.sunset))
    st = False
    for p in (ME, VE, MA, JU, SA):
        s0, s1 = _calc(c.jd - 1, _SWE_ID[p])[1], _calc(c.jd + 1, _SWE_ID[p])[1]
        st = st or (s0 * s1 < 0)
    flags["station"] = st
    flags["any"] = any(flags.values())
    return flags


# ================================================================== match API
def analyse(dt_utc, lat, lon, fav_name, und_name, draw_possible=True, clear_favourite=True,
            nation_fav=None, nation_und=None):
    c = compute_chart(dt_utc, lat, lon)
    r = rao(c, nation_fav, nation_und)
    k = chokoisky(c, fav_name, und_name)
    f = frawley(c) if clear_favourite else None
    s = sandhi(c)
    return synthesise(r, k, f, s, draw_possible) | {"rao": r, "chokoisky": k, "frawley": f, "sandhi": s}


def synthesise(r, k, f, s, draw_possible=True, weights=None):
    """Section 8 synthesis: weighted vote + confidence score."""
    w = weights or {"rao": 1.0, "chokoisky": 1.0, "frawley": 1.0}
    verdicts = {"rao": r["verdict"], "chokoisky": k["verdict"]}
    if f:
        verdicts["frawley"] = f["verdict"]
    if not draw_possible:
        verdicts = {e: (v if v != "draw" else "fav") for e, v in verdicts.items()}
    tally = {}
    for e, v in verdicts.items():
        tally[v] = tally.get(v, 0) + w[e]
    winner = max(tally, key=tally.get)
    agree = sum(1 for v in verdicts.values() if v == winner)
    if agree == 1 and f:
        winner = verdicts["frawley"]                     # no consensus -> lean Frawley
    conf = {3: 40, 2: 25, 1: 10}[agree]
    conf += 15 * (abs(r["diff"]) > 8) + 15 * (abs(k["total"]) > 9)
    conf += 15 * (f is not None and sum(1 for tm, wt, _ in f["testimonies"] if tm == winner and wt >= 3) >= 2)
    conf += 10 * k["d9_cusp_planet"] + 5 * k["sky"]
    conf -= 15 * s["any"] + 15 * r["saturn_8th"]
    pattern = ("all_agree" if len(set(verdicts.values())) == 1 and len(verdicts) == 3 else
               "rao_chokoisky_agree" if verdicts["rao"] == verdicts["chokoisky"] else
               "rao_frawley_agree" if f and verdicts["rao"] == verdicts.get("frawley") else
               "chokoisky_frawley_agree" if f and verdicts["chokoisky"] == verdicts.get("frawley") else
               "all_disagree")
    return {"consensus": winner, "agreement": agree, "pattern": pattern,
            "confidence": max(0, min(100, conf)), "verdicts": verdicts}
