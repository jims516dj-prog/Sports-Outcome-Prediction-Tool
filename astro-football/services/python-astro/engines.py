"""The three analysis engines (spec sections 5, 6, 7), sandhi guardrails (10.2) and
the comparative synthesis (8).

Every engine reasons from the favourite's point of view (favourite = Native / Lagna /
1st house, underdog = Rival / 7th house) and its output is mapped back to Team A / B.
"""
from __future__ import annotations

import math
from functools import lru_cache

import swisseph as swe

from chart import (DAY_LORDS, DAY_NAMES, GRAHAS, JU, KE, MA, ME, MO, NE, PL, RA, SA, SU, VE, UK, UR, GU, CH, CE,
                   Chart, _calc, SWE_ID, antiscion, d9, fmt_deg, fortuna, nak_lord, norm, sep, signed,
                   sub_lord, vedic_weekday)
from reference import (BENEFICS, BRIGHTNESS, COLOR_PLANET, D1_EFFECT, D9_EFFECT, D9_MEANING, DEFAULT_TOGGLES,
                       DIG_BALA_HOUSE, EXALT, INVISIBLE, JERSEY_QUALITY, KEY_STARS, MALEFICS, MEAN_SPEED,
                       NUMBER_PLANET, PADA_SYLLABLES, PLANET_NAMES, SIGN_LORD, SIGNS, dignity, reduce_digit,
                       relation)

N = PLANET_NAMES


def od(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _toggles(t):
    out = {k: dict(v) for k, v in DEFAULT_TOGGLES.items()}
    for k, v in (t or {}).items():
        out.setdefault(k, {}).update(v)
    return out


def vedic_aspects(p, from_sign):
    extra = {MA: [4, 8], JU: [5, 9], SA: [3, 10], RA: [5, 9], KE: [5, 9]}.get(p, [])
    return {(from_sign + k - 1) % 12 for k in [7] + extra}


def moon_waxing(c):
    return norm(c.trop[MO] - c.trop[SU]) < 180


# ====================================================================== ENGINE 1: RAO
RAO_PARAMS = [("ascendant", "Ascendant"), ("asc_lord", "Ascendant lord"), ("score", "Score"),
              ("game_coach", "Game + Coach & Captain"), ("fans_odds", "Fans & Odds"), ("penalties", "Penalties"),
              ("nation_moon", "Nation/club Moon"), ("nation_asc", "Nation/club Ascendant"),
              ("planetary_influence", "Planetary influence")]


def rao(c: Chart, inp: dict, toggles=None) -> dict:
    tg = _toggles(toggles)["rao"]
    sign_of = {p: c.sign(p) for p in GRAHAS}
    lagna = c.lagna_sid_sign

    def quality(p):
        benefic = p in BENEFICS and not (p == MO and not moon_waxing(c))
        q = 1.0 if benefic else -1.0
        d = dignity(p, sign_of[p])
        if d >= 1:
            q *= 1.5 if q > 0 else 0.5
        elif d < 0:
            q = q * 0.5 if q > 0 else q * 1.5
        return q

    def influence(sign, exclude=(), heavy=False):
        net, desc = 0.0, []
        lord = SIGN_LORD[sign]
        for p in GRAHAS:
            if p in exclude:
                continue
            occ = sign_of[p] == sign
            asp = sign in vedic_aspects(p, sign_of[p])
            w = 1.0 if occ else (0.75 if asp else 0)
            if not w:
                continue
            if heavy and p in (SA, JU, MA):
                w *= 1.5
            rel = relation(p, lord)
            net += w * (quality(p) + 0.5 * rel)
            dg = {2: " exalted", 1: " in own sign", -1: " debilitated"}.get(dignity(p, sign_of[p]), "")
            kind = "occupies" if occ else "aspects"
            desc.append(f"{N[p]}{dg} {kind} ({'friend' if rel > 0 else 'enemy' if rel < 0 else 'neutral'} of {N[lord]})")
        return net, desc

    def pts(net):
        return 0 if net <= -0.5 else (1 if net < 0.5 else (2 if net < 2 else 3))

    def house(sign):
        net, desc = influence(sign)
        lord = SIGN_LORD[sign]
        dg = dignity(lord, sign_of[lord])
        net += 0.5 * max(-1, min(1, dg))
        if dg:
            desc.append(f"lord {N[lord]} {'strong' if dg > 0 else 'debilitated'}")
        return pts(net), desc

    def team(l, label):
        H = lambda n: (l + n - 1) % 12
        out, md = {}, []
        for key, n in (("ascendant", 1), ("score", 10), ("fans_odds", 2), ("penalties", 12)):
            p, d = house(H(n))
            out[key] = p
            md.append(f"- **{dict(RAO_PARAMS)[key]}** ({od(n if label == 'Native' else (n + 5) % 12 + 1)}, "
                      f"{SIGNS[H(n)]}): {p} pts - {', '.join(d) or 'no planet, no aspect (neutral)'}")
        lord = SIGN_LORD[l]
        h_from = (sign_of[lord] - l) % 12 + 1
        net, d = influence(sign_of[lord], exclude=(lord,))
        net += {1: 1, 4: 1, 5: 1, 9: 1, 10: 1, 11: 0.5, 6: -1, 8: -1, 12: -1}.get(h_from, 0)
        net += max(-1, min(1, dignity(lord, sign_of[lord])))
        out["asc_lord"] = pts(net)
        md.insert(1, f"- **Ascendant lord** {N[lord]} in {SIGNS[sign_of[lord]]} ({od(h_from)} from own lagna): "
                     f"{out['asc_lord']} pts - {', '.join(d) or 'unaspected'}")
        g5, d5 = house(H(5))
        g3, d3 = house(H(3))
        out["game_coach"] = round((g5 + g3) / 2, 1)
        md.append(f"- **Game + Coach & Captain** ({SIGNS[H(5)]} / {SIGNS[H(3)]}): {out['game_coach']} pts - "
                  f"game: {', '.join(d5) or 'neutral'}; coach: {', '.join(d3) or 'neutral'}")
        return out, md

    fav, md_f = team(lagna, "Native")
    und, md_u = team((lagna + 6) % 12, "Rival")
    caveats = []

    # Step 2: Nations' charts
    nation_ok = tg.get("nation_charts", True)
    for side, natal, l, store, md in (("fav", inp.get("natal_fav"), lagna, fav, md_f),
                                      ("und", inp.get("natal_und"), (lagna + 6) % 12, und, md_u)):
        if not nation_ok or not natal:
            continue
        for key, s in (("nation_moon", natal.get("moon_sign")), ("nation_asc", natal.get("asc_sign"))):
            if s is None:
                continue
            net, d = influence(s, heavy=True)
            h = (s - l) % 12 + 1
            net += 0.5 if h in (1, 3, 10, 11) else (-0.5 if h in (6, 8, 12) else 0)
            store[key] = pts(net)
            md.append(f"- **{dict(RAO_PARAMS)[key]}** {SIGNS[s]} falls in the {od(h)} of the match chart: "
                      f"{store[key]} pts - {', '.join(d) or 'no transit influence'}")
        ref = natal.get("asc_sign") if natal.get("asc_sign") is not None else natal.get("moon_sign")
        eighth = (ref + 7) % 12
        if sign_of[SA] == eighth or eighth in vedic_aspects(SA, sign_of[SA]):
            caveats.append(f"Saturn on the 8th of the {'favourite' if side == 'fav' else 'underdog'}'s nation/club "
                           "chart - interruption risk (Rao p.30): set the prediction aside if the match is interrupted")
    if not (inp.get("natal_fav") or inp.get("natal_und")) or not nation_ok:
        caveats.append("Unable to run Nations' Charts phase - founding chart missing; Game Analysis "
                       "+ Planetary Influence still computed")

    # Step 3: Planetary influence (captain jersey, day, jersey colour)
    pi_on = tg.get("planetary_influence", True) and inp.get("has_captain_data")
    if pi_on:
        wd = vedic_weekday(c)
        day_lord = DAY_LORDS[wd]
        date_planet = NUMBER_PLANET[reduce_digit(c.dt_utc.day)]
        for store, md, jersey, color in ((fav, md_f, inp.get("captain_fav"), inp.get("color_fav")),
                                         (und, md_u, inp.get("captain_und"), inp.get("color_und"))):
            net, parts = 0.0, []
            if jersey:
                n = reduce_digit(jersey)
                jp = NUMBER_PLANET[n]
                net += relation(jp, date_planet) + 0.5 * relation(jp, day_lord) + 0.5 * relation(jp, MA)
                net += JERSEY_QUALITY.get(n, 0)
                parts.append(f"jersey {jersey}→{n} = {N[jp]}; vs date planet {N[date_planet]}: "
                             f"{['enemy', 'neutral', 'friend'][relation(jp, date_planet) + 1]}; vs day lord "
                             f"{N[day_lord]}: {['enemy', 'neutral', 'friend'][relation(jp, day_lord) + 1]}")
            if color in COLOR_PLANET:
                cp = COLOR_PLANET[color]
                net += 0.5 * relation(cp, day_lord)
                parts.append(f"colour {color} = {N[cp]} vs day lord {N[day_lord]}: "
                             f"{['enemy', 'neutral', 'friend'][relation(cp, day_lord) + 1]}")
            store["planetary_influence"] = pts(net)
            md.append(f"- **Planetary influence**: {store['planetary_influence']} pts - {'; '.join(parts)} "
                      f"({DAY_NAMES[wd]}; football's influencing planet is Mars)")
    else:
        caveats.append("Planetary influence layer skipped - captain/jersey data not provided")

    tf, tu = sum(fav.values()), sum(und.values())
    diff = tf - tu
    debil = [N[p] for p in GRAHAS if dignity(p, sign_of[p]) < 0]
    if debil:
        caveats.append("Debilitated: " + ", ".join(debil))
    verdict = "fav" if diff > 0 else ("und" if diff < 0 else "draw")
    margin = abs(diff)
    gd = (2, 3) if margin >= 8 else ((1, 2) if margin >= 4 else ((1, 1) if verdict != "draw" else (0, 0)))
    md = (["### Native (favourite) - read from the Lagna", *md_f, "",
           "### Rival (underdog) - read from the 7th", *md_u, "",
           f"**Totals:** favourite {tf:g} vs underdog {tu:g} (difference {diff:+g}). "
           + ("A margin of 8+ points suggests a decisive win." if margin >= 8 else
              "A 1-3 point margin suggests a close match." if 1 <= margin <= 3 else "")])
    return {"engine": "rao", "lagna": SIGNS[lagna], "fav": fav, "und": und, "total_fav": tf, "total_und": tu,
            "diff": diff, "verdict": verdict, "goal_diff_range": list(gd),
            "confidence": "high" if margin >= 8 else ("medium" if margin >= 4 else "low"),
            "planetary_influence_included": bool(pi_on), "saturn_8th": any("Saturn on the 8th" in x for x in caveats),
            "caveats": caveats, "markdown": "\n".join(md)}


# ====================================================================== ENGINE 2: CHOKOISKY
FAV_HOUSES, UND_HOUSES = {1, 3, 6, 10, 11}, {7, 9, 12, 4, 5}


@lru_cache(maxsize=4096)
def _star_sid(name, jd_day):
    try:
        lon = swe.fixstar2_ut(name, jd_day)[0][0]
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        return norm(lon - swe.get_ayanamsa_ut(jd_day))
    except Exception:
        return KEY_STARS[name][0]


def name_matches(syl, name):
    import unicodedata
    if not name:
        return 0
    skip = {"fc", "afc", "cf", "ac", "as", "ss", "ssc", "us", "sc", "sv", "vfl", "vfb", "tsg", "rc", "rcd", "cd",
            "ud", "sd", "ca", "club", "de", "real", "1.", "fsv", "the", "calcio", "olympique", "stade", "athletic"}
    words = [w for w in name.split() if w.lower() not in skip and not w.isdigit()]
    if not words:
        return 0
    w = unicodedata.normalize("NFKD", words[0].lower())
    w = "".join(ch for ch in w if ch.isalpha()).replace("ch", "#")
    for a, b in (("w", "v"), ("f", "ph"), ("z", "jh"), ("q", "k"), ("c", "k"), ("x", "ks"), ("y", "i")):
        w = w.replace(a, b)
    w = w.replace("#", "ch")
    variants = {syl}
    if syl.endswith("e"):
        variants.add(syl[:-1] + "ai")                 # diphthong rule eh -> ai
    if syl.endswith("o"):
        variants.add(syl[:-1] + "au")                 # oh -> au
    if syl.startswith("ph"):
        variants.add("p" + syl[2:])
    if syl.startswith("p"):
        variants.add("ph" + syl[1:])
    return int(any(w.startswith(v) for v in variants))


def chokoisky(c: Chart, inp: dict, toggles=None) -> dict:
    tg = _toggles(toggles)["chokoisky"]
    rows = {}
    house = {p: c.house_of(c.trop[p]) for p in c.trop if p != "TrueNode"}
    sid_sign = {p: int(c.sid(p) // 30) for p in GRAHAS}
    elong = norm(c.trop[MO] - c.trop[SU])

    def exaggerated(p):
        s = sid_sign[p]
        return (dignity(p, s) >= 1 or c.retro(p) or nak_lord(c.sid(p)) == p
                or DIG_BALA_HOUSE.get(p) == house[p] or (p == MO and abs(elong - 180) < 12))

    # Technique 1 - Victory houses
    if tg["victory_houses"]:
        vh, det = 0.0, []
        for p in GRAHAS:
            if p in MALEFICS:
                d = dignity(p, sid_sign[p])
                pts = 2.0 if d < 0 else (3.0 if (d >= 1 or DIG_BALA_HOUSE.get(p) == house[p]) else 2.5)
            elif p in BENEFICS and dignity(p, sid_sign[p]) < 0:
                pts = 2.0
            elif p in BENEFICS and exaggerated(p):
                pts = 2.5
            else:
                continue
            if house[p] in FAV_HOUSES:
                vh += pts
                det.append(f"{N[p]} in {od(house[p])} (+{pts})")
            elif house[p] in UND_HOUSES:
                vh -= pts
                det.append(f"{N[p]} in {od(house[p])} (-{pts})")
        rows["victory_houses"] = (vh, "; ".join(det))

    # Technique 2 - SKY / PKY
    def hemmed(h):
        before, after = (h - 2) % 12 + 1, h % 12 + 1
        side = lambda hh: {p for p in GRAHAS if house[p] == hh}
        a, b = side(before), side(after)
        if not a or not b:
            return 0.0, ""
        ben = lambda s: all(p in BENEFICS for p in s)
        mal = lambda s: all(p in MALEFICS for p in s)
        if ben(a) and ben(b):
            return 8.0, "full SKY"
        if (ben(a) and b <= {SU, KE}) or (ben(b) and a <= {SU, KE}):
            return 3.5, "marred SKY"
        if mal(a) and mal(b):
            if (a | b) <= {RA, KE} and len(a | b) == 1:
                return -3.5, "half PKY (single node)"
            return -7.0, "PKY"
        return 0.0, ""
    if tg["sky_pky"]:
        h1, l1 = hemmed(1)
        h7, l7 = hemmed(7)
        rows["sky_pky"] = (h1 - h7, "; ".join(x for x in (f"{l1} around Lagna" if l1 else "",
                                                          f"{l7} around 7th" if l7 else "") if x))
        sky_present = h1 > 0 or h7 > 0
    else:
        sky_present = False

    # Technique 3 - D1 cuspal strength
    sid_cusp_sign = lambda i: int(c.sid_pt(c.cusps[i - 1]) // 30)
    fav_lorded = {SIGN_LORD[sid_cusp_sign(h)] for h in FAV_HOUSES}
    und_lorded = {SIGN_LORD[sid_cusp_sign(h)] for h in UND_HOUSES}

    def eff(e, p, team_sign):
        if e == "M":
            return 1 if ME in (fav_lorded if team_sign > 0 else und_lorded) else -1
        if e == "UR":
            return -1 if c.retro(UR) else 1
        if e == "NE":
            return 1 if c.retro(NE) else -1
        return e

    if tg["d1_cusps"]:
        cusp_team = {1: (1, 0), 7: (-1, 0), 10: (1, 1), 4: (-1, 1), 6: (1, 2), 12: (-1, 2)}
        d1v, det = 0.0, []
        for h, (ts, axis) in cusp_team.items():
            for p in D1_EFFECT:
                ex = p in EXALT and EXALT[p] == sid_sign.get(p)
                orb = (2.0 if p in INVISIBLE else 2.5) + (0.5 if (c.retro(p) or ex) else 0)
                if sep(c.trop[p], c.cusps[h - 1]) <= orb:
                    e = eff(D1_EFFECT[p][axis], p, ts)
                    v = ts * e * (7 if p in INVISIBLE else 8)
                    d1v += v
                    if v:
                        det.append(f"{N[p]} on {od(h)} cusp ({v:+g})")
        rows["d1_cusps"] = (d1v, "; ".join(det))

    # Technique 4 - Navamsha cuspal strength (tier 3)
    d9_present = d9_jup_fav = d9_sat_fav = d9_mars = False
    if tg["d9_cusps"]:
        asc9 = d9(c.sid_pt(c.asc))
        d9v, det = 0.0, []
        for p in D9_EFFECT:
            pl = d9(c.sid(p))
            orb = 2.0 if p in INVISIBLE else 2.5
            for ts, cusp, lab in ((1, asc9, "D9 Lagna"), (-1, norm(asc9 + 180), "D9 7th")):
                dist = sep(pl, cusp)
                if dist <= orb:
                    e = eff(D9_EFFECT[p], p, ts)
                    w = 13.5 if p in INVISIBLE else 16
                    if dist < 1 and sep(c.trop[p], c.cusps[0 if ts > 0 else 6]) < 10:
                        w *= 1.25                                   # "double whammy" (Chokoisky p.110)
                    d9v += ts * e * w
                    d9_present = d9_present or e != 0
                    d9_jup_fav |= p == JU and ts > 0
                    d9_sat_fav |= p == SA and ts > 0
                    d9_mars |= p == MA
                    det.append(f"{N[p]} on {lab} ({D9_MEANING[p]}; {ts * e * w:+g})")
        rows["d9_cusps"] = (d9v, "; ".join(det))

    # Technique 5 - Nama pada
    syl = PADA_SYLLABLES[int(c.sid_pt(c.mc) // (360 / 108)) % 108]
    np_f = name_matches(syl, inp.get("fav_name", ""))
    np_u = name_matches(syl, inp.get("und_name", ""))
    if tg["nama_pada"]:
        rows["nama_pada"] = (16.0 * (np_f - np_u),
                             f"MC navamsha syllable '{syl}'" + (" matches the favourite" if np_f else "")
                             + (" matches the underdog" if np_u else ""))

    # Technique 6 - KP sublords
    kp_cusp_sign = lambda i: int(c.sid_pt(c.cusps[i - 1], kp=True) // 30)
    owned = {p: [i for i in range(1, 13) if SIGN_LORD[kp_cusp_sign(i)] == p] for p in GRAHAS}
    for node in (RA, KE):
        owned[node] = owned[SIGN_LORD[int(c.sid(node, kp=True) // 30)]]

    def hf(h):
        return 1 if h in FAV_HOUSES else (0.5 if h == 2 else (-1 if (h in UND_HOUSES or h == 8) else 0))

    def kp(p):
        star = nak_lord(c.sid(p, kp=True))
        return (4 * hf(house[star]) + 3 * hf(house[p]) + 2 * sum(hf(h) for h in owned[star])
                + sum(hf(h) for h in owned[p]))
    sl = [sub_lord(c.sid_pt(x, kp=True)) for x in c.cusps]
    sub_diff = kp(sl[0]) + kp(sl[6])
    if tg["sublords"]:
        array = 0.0
        sigs = [hf(house[p]) for p in sl]
        if all(s > 0 for s in sigs):
            array = 8.0
        elif all(s < 0 for s in sigs):
            array = -8.0
        rows["sublords"] = (8 * math.tanh(sub_diff / 8) + array,
                            f"1st-cusp sublord {N[sl[0]]} ({kp(sl[0]):+g}), 7th-cusp sublord {N[sl[6]]} "
                            f"({kp(sl[6]):+g}); difference {sub_diff:+g}"
                            + ("; sublord array" if array else "") + ("; ≤3 suggests a draw" if abs(sub_diff) <= 3 else ""))

    # Technique 7 - Nakshatra taras
    tara_hits = []
    if tg["nakshatra_tara"]:
        jd_day = math.floor(c.jd)
        stars = {n: _star_sid(n, jd_day) for n in KEY_STARS}
        tv = 0.0
        for ts, hs in ((1, (1, 10)), (-1, (7, 4))):
            pts_ = [(f"{od(h)} cusp", c.sid_pt(c.cusps[h - 1])) for h in hs] + \
                   [(f"lord of {od(h)} ({N[SIGN_LORD[sid_cusp_sign(h)]]})", c.sid(SIGN_LORD[sid_cusp_sign(h)]))
                    for h in hs]
            for lab, x in pts_:
                for name, pos in stars.items():
                    if sep(x, pos) <= 1.0:
                        tv += ts * KEY_STARS[name][1]
                        tara_hits.append(f"{name} on {lab} ({'fav' if ts > 0 else 'und'}: {KEY_STARS[name][2]})")
        rows["nakshatra_tara"] = (tv, "; ".join(tara_hits))

    # Technique 8 - Planetary war
    war_winner = None
    if tg["planetary_war"]:
        fav_l = {SIGN_LORD[sid_cusp_sign(h)] for h in (1, 10)}
        und_l = {SIGN_LORD[sid_cusp_sign(h)] for h in (7, 4)}
        wv, det = 0.0, []
        for i, a in enumerate(BRIGHTNESS):
            for b in BRIGHTNESS[i + 1:]:
                if sep(c.trop[a], c.trop[b]) <= 1.0:
                    v = 5 * ((a in fav_l) - (a in und_l)) - 5 * ((b in fav_l) - (b in und_l))
                    wv += v
                    if v:
                        war_winner = "fav" if v > 0 else "und"
                        det.append(f"{N[a]} defeats {N[b]} ({v:+g})")
        rows["planetary_war"] = (wv, "; ".join(det))

    total = sum(v for v, _ in rows.values())
    verdict = "fav" if total > 3 else ("und" if total < -3 else "draw")
    conf = "high" if abs(total) > 9 else ("medium" if abs(total) >= 5 else "low")
    gd = round(abs(total) / inp.get("goal_divisor", 3.0))
    if not inp.get("draw_possible", True) and verdict == "draw":
        verdict = "fav" if total >= 0 else "und"
    decisive = [f"{k}: {d}" for k, (v, d) in rows.items() if abs(v) >= 8 and d]
    return {"engine": "chokoisky", "rows": {k: {"points": round(v, 2), "detail": d} for k, (v, d) in rows.items()},
            "total": round(total, 2), "verdict": verdict, "goal_diff": gd, "confidence": conf,
            "d9_cusp_planet": d9_present, "d9_jupiter_on_fav_cusp": d9_jup_fav, "d9_saturn_on_fav_cusp": d9_sat_fav,
            "d9_mars_on_cusp": d9_mars, "sky": sky_present, "sublord_diff": round(sub_diff, 2),
            "nama_pada_fav": np_f, "nama_pada_und": np_u, "mc_syllable": syl, "tara_hits": tara_hits,
            "planetary_war_winner": war_winner, "decisive": decisive}


# ====================================================================== ENGINE 3: FRAWLEY
ASPECTS = {0: "conjunction", 60: "sextile", 90: "square", 120: "trine", 180: "opposition"}


def frawley(c: Chart, inp: dict, toggles=None) -> dict:
    tg = _toggles(toggles)["frawley"]
    t = c.trop
    cusp = {h: c.cusps[h - 1] for h in (1, 2, 4, 7, 10)}
    lord = {h: SIGN_LORD[c.trop_sign(cusp[h])] for h in (1, 4, 7, 10)}
    team_of_lord = {}
    for h, p in lord.items():
        team_of_lord.setdefault(p, set()).add("fav" if h in (1, 10) else "und")
    T = []

    def add(team, w, text, kind):
        T.append({"team": team, "weight": w, "strength": "strong" if w >= 3 else ("medium" if w >= 2 else "weak"),
                  "text": text, "kind": kind})

    def place(x, h):
        if c.trop_sign(x) != c.trop_sign(cusp[h]):
            return None
        d = signed(cusp[h], x)
        return "on" if -3 <= d < 0 else ("in" if 0 <= d <= 3 else None)

    TABLE = {(1, 7, "on"): ("fav", 3), (1, 7, "in"): ("und", 3), (7, 1, "on"): ("und", 3),
             (7, 1, "in"): ("fav", 3), (10, 7, "on"): ("fav", 2), (10, 7, "in"): ("und", 2),
             (7, 10, "on"): ("und", 2), (7, 10, "in"): ("fav", 2), (1, 1, "on"): ("fav", 1),
             (1, 1, "in"): ("fav", 1), (4, 4, "on"): ("und", 1), (4, 4, "in"): ("und", 1),
             (10, 10, "on"): ("fav", 1), (10, 10, "in"): ("fav", 1)}
    modes = [("body", lambda p: t[p])] if tg["house_placement"] else []
    if tg["antiscia"]:
        modes.append(("antiscion", lambda p: antiscion(t[p])))
    for (lh, ch, mode), (team, s) in TABLE.items():
        p = lord[lh]
        for label, fn in modes:
            if place(fn(p), ch) == mode:
                enemy = ch != lh
                if c.retro(p) and mode == "in" and enemy:
                    continue
                w = s * (0.5 if (c.retro(p) and mode == "on" and enemy) else 1)
                add(team, w, f"Lord {lh} ({N[p]}) {label} {'on' if mode == 'on' else 'just inside'} the {od(ch)} cusp"
                    + (" (retrograde - weaker)" if c.retro(p) and enemy else ""), "placement")

    if tg["moon_placement"]:
        for x, label in ((t[MO], "Moon"), (antiscion(t[MO]), "Moon's antiscion")):
            for h, team in ((1, "fav"), (10, "fav"), (7, "und"), (4, "und")):
                if place(x, h):
                    add(team, 1.5, f"{label} at the {od(h)} cusp", "moon")

    pof = fortuna(c)
    apof = antiscion(pof)
    if tg["fortuna"]:
        for h, team in ((1, "fav"), (7, "fav"), (10, "fav"), (4, "und")):
            if sep(apof, cusp[h]) <= 3:
                add(team, 3, f"Antiscion of Fortuna close to the {od(h)} cusp", "fortuna")
        if sep(pof, t[SU]) <= 2:
            add("und", 1, "Fortuna combust - harms the favourite", "fortuna")

    # Moon's applying aspects
    rng = inp.get("moon_range", 5.0) + (inp.get("extra_time_deg", 1.0) if inp.get("extra_time") else 0)
    to_sign_end = 30 - (t[MO] % 30)
    events, late, last = [], False, None
    if tg["moon_aspects"]:
        for h, p in lord.items():
            if p == MO:
                continue
            rel = c.speed[MO] - c.speed.get(p, 0)
            if rel <= 0:
                continue
            for ang in ASPECTS:
                for sg in (1, -1):
                    gap = norm(norm(t[p] + sg * ang) - t[MO])
                    travel = gap * c.speed[MO] / rel
                    if 0 < travel <= min(rng, to_sign_end):
                        events.append((travel, ASPECTS[ang], f"Lord {h} ({N[p]})", "fav" if h in (1, 10) else "und"))
        for pt, lab in ((pof, "Fortuna"), (apof, "the antiscion of Fortuna")):
            for ang in ASPECTS:
                for sg in (1, -1):
                    gap = norm(norm(pt + sg * ang) - t[MO])
                    if 0 < gap <= min(rng, to_sign_end):
                        events.append((gap, ASPECTS[ang], lab, "fortuna"))
        events.sort()
        for travel, asp, lab, team in events:
            if team == "fortuna":
                win = "fav" if asp in ("conjunction", "trine", "sextile") else "und"
                add(win, 3, f"Moon {asp} {lab} after {travel:.1f}° - final", "moon_aspect")
                late, last = travel > 0.7 * rng, None
                break
            last, late = (team, asp, lab, travel), travel > 0.7 * rng
            if asp == "conjunction":
                break
        if last:
            add(last[0], 3, f"Moon's last aspect within range: {last[1]} {last[2]} after {last[3]:.1f}°", "moon_aspect")

    if tg["fortuna"]:
        for p, lab, team in ((lord[1], "Lord 1", "fav"), (lord[7], "Lord 7", "und")):
            for pt, plab in ((pof, "Fortuna"), (apof, "the antiscion of Fortuna")):
                d = sep(t[p], pt)
                if d <= 3:
                    add(team, 2, f"{lab} ({N[p]}) conjunct {plab}", "fortuna")
                elif abs(d - 180) <= 3:
                    w = team if (lab == "Lord 7" and plab == "Fortuna") else ("und" if lab == "Lord 1" else "fav")
                    add(w, 2, f"{lab} ({N[p]}) opposite {plab}", "fortuna")

    if tg["dispositor"]:
        disp = SIGN_LORD[c.trop_sign(pof)]
        if disp not in (lord[1], lord[7], MO):
            sgn = 1 if c.speed.get(disp, 0) > 0 else -1
            if 0 < signed(t[disp], pof) * sgn <= 3:
                add("fav", 1.5, f"Dispositor of Fortuna ({N[disp]}) applying to conjunct Fortuna", "dispositor")
            if 0 < signed(t[disp], norm(pof + 180)) * sgn <= 3:
                add("und", 1.5, f"Dispositor of Fortuna ({N[disp]}) applying to oppose Fortuna", "dispositor")

    if tg["misc"]:
        nn, sn = t["TrueNode"], norm(t["TrueNode"] + 180)
        for p, teams in team_of_lord.items():
            for team in teams:
                other = "und" if team == "fav" else "fav"
                if sep(t[p], nn) <= 3:
                    add(team, 1, f"North Node on {N[p]}", "misc")
                if sep(t[p], sn) <= 3:
                    add(other, 1, f"South Node on {N[p]}", "misc")
                if p != SU and 17 / 60 < sep(t[p], t[SU]) <= 2:
                    add(other, 1.5, f"{N[p]} combust", "misc")
                if SA not in (lord[1], lord[7]) and p != SA and sep(t[p], t[SA]) <= 3:
                    add(other, 1, f"Saturn afflicts {N[p]}", "misc")
        if place(t[PL], 1) or sep(t[PL], cusp[1]) <= 3:
            add("und", 2, "Pluto on the 1st cusp - destructive to the favourite", "misc")
        if any(sep(t[PL], x) <= 3 or abs(sep(t[PL], x) - 180) <= 3 for x in (pof, apof)):
            add("und", 1.5, "Pluto conjunct/opposite Fortuna or its antiscion", "misc")
        if place(t[PL], 2):
            add("und", 0.5, "Pluto on the 2nd cusp", "misc")
        if 0 < signed(t[UR], c.mc) * (1 if c.speed[UR] > 0 else -1) <= 3:
            add("fav", 2, "Uranus applying to the MC", "misc")
        if sep(t[UR], pof) <= 3:
            add("fav", 1.5, "Uranus conjunct Fortuna", "misc")
        if abs(sep(t[UR], pof) - 180) <= 3:
            add("und", 1.5, "Uranus opposite Fortuna", "misc")

    score = sum(x["weight"] if x["team"] == "fav" else -x["weight"] for x in T)
    if not T:
        verdict, default = "fav", True
    else:
        default = False
        verdict = "fav" if score > 0.5 else ("und" if score < -0.5 else "draw")
    if not inp.get("draw_possible", True) and verdict == "draw":
        verdict = "fav" if score >= 0 else "und"
    n_win = sum(1 for x in T if x["team"] == verdict)
    strong = sum(1 for x in T if x["team"] == verdict and x["strength"] == "strong")
    gw = min(4, 1 + n_win // 2)
    return {"engine": "frawley", "lords": {f"L{h}": N[p] for h, p in lord.items()}, "testimonies": T,
            "score": round(score, 2), "verdict": verdict, "default_rule": default,
            "goals": {"winner": gw if verdict != "draw" else 1, "loser": 0 if gw <= 2 or verdict == "draw" else 1}
            if verdict != "draw" else {"winner": 1, "loser": 1},
            "late_goal": late, "strong_count": strong, "n_testimonies": len(T),
            "lord1_on_7th": any(x["text"].startswith("Lord 1") and "7th cusp" in x["text"] and x["team"] == "fav" for x in T),
            "lord7_on_1st": any(x["text"].startswith("Lord 7") and "1st cusp" in x["text"] and x["team"] == "und" for x in T),
            "pluto_on_1st": any("Pluto on the 1st" in x["text"] for x in T),
            "moon_final_aspect_to": (last[2].split(" (")[0].replace(" ", "") if last else "none"),
            "antiscion_fortuna_on_1_or_7": any("Antiscion of Fortuna" in x["text"] and
                                               ("1st cusp" in x["text"] or "7th cusp" in x["text"]) for x in T),
            "confidence": "high" if strong >= 2 else ("medium" if strong == 1 else "low")}


# ====================================================================== SANDHI (10.2)
@lru_cache(maxsize=None)
def _eclipses(y0=1950, y1=2060):
    out = []
    for fn in (lambda j: swe.sol_eclipse_when_glob(j, swe.FLG_SWIEPH)[1][0],
               lambda j: swe.lun_eclipse_when(j, swe.FLG_SWIEPH)[1][0]):
        jd, end = swe.julday(y0, 1, 1, 0), swe.julday(y1, 1, 1, 0)
        while jd < end:
            tt = fn(jd)
            out.append(tt)
            jd = tt + 20
    return tuple(sorted(out))


def moon_void(c: Chart):
    """No applying Ptolemaic aspect of the Moon to Sun..Saturn before it leaves its sign."""
    t = c.trop
    to_end = 30 - t[MO] % 30
    for p in (SU, ME, VE, MA, JU, SA):
        rel = c.speed[MO] - c.speed[p]
        for ang in ASPECTS:
            for sg in (1, -1):
                gap = norm(norm(t[p] + sg * ang) - t[MO])
                if rel > 0 and gap * c.speed[MO] / rel <= to_end:
                    return False
    return True


def sandhi(c: Chart):
    ecl = [e for e in _eclipses() if abs(c.jd - e) <= 3]
    f = {"eclipse_window": bool(ecl), "sankranti": c.sid(SU) % 30 >= 29,
         "sunrise_sunset": any(x is not None and abs(c.jd - x) * 1440 <= 30 for x in (c.sunrise, c.sunset))}
    stations = []
    for p in ("Me", "Ve", "Ma", "Ju", "Sa"):
        s0, s1 = _calc(c.jd - 1, SWE_ID[p])[1], _calc(c.jd + 1, SWE_ID[p])[1]
        if s0 * s1 < 0 or abs(c.speed[p]) < 0.1 * MEAN_SPEED[p]:
            stations.append(N[p])
    f["station"] = bool(stations)
    f["moon_void_of_course"] = moon_void(c)
    warnings = []
    if f["eclipse_window"]:
        warnings.append("Kickoff within 3 days of an eclipse")
    if f["sankranti"]:
        warnings.append("Solar sankranti - Sun at 29°+ of its sidereal sign")
    if f["sunrise_sunset"]:
        warnings.append("Kickoff within 30 minutes of sunrise/sunset at the venue")
    if stations:
        warnings.append("Stationary within 24 h: " + ", ".join(stations))
    if f["moon_void_of_course"]:
        warnings.append("Moon void of course (flag only - not a block for Frawley's event chart)")
    f["any"] = bool(warnings) and not (len(warnings) == 1 and f["moon_void_of_course"])
    f["warnings"] = warnings
    return f


# ====================================================================== SYNTHESIS (8)
def to_team(v, fav_side):
    if v in ("draw", "disabled", None):
        return v or "disabled"
    return fav_side if v == "fav" else ("B" if fav_side == "A" else "A")


def synthesise(r, k, f, s, inp, engine_weights=None):
    fav_side = inp["fav_side"]
    w = {"rao": 1.0, "chokoisky": 1.0, "frawley": 1.0} | (engine_weights or {})
    v = {}
    if r:
        v["rao"] = to_team(r["verdict"], fav_side)
    if k:
        v["chokoisky"] = to_team(k["verdict"], fav_side)
    if f:
        v["frawley"] = to_team(f["verdict"], fav_side)
    tally = {}
    for e, x in v.items():
        tally[x] = tally.get(x, 0) + w[e]
    winner = max(tally, key=tally.get) if tally else "draw"
    agree = sum(1 for x in v.values() if x == winner)
    names = {"rao": "Rao", "chokoisky": "Chokoisky", "frawley": "Frawley"}
    team_name = lambda x: {"A": inp["team_a"], "B": inp["team_b"], "draw": "Draw"}.get(x, x)
    if len(v) == 3 and agree == 3:
        headline = f"Very strong consensus: {team_name(winner)}"
    elif agree == 2:
        dissent = [names[e] for e, x in v.items() if x != winner]
        headline = f"Strong consensus: {team_name(winner)}" + (f" (one dissent: {dissent[0]})" if dissent else "")
    else:
        if "frawley" in v:
            winner = v["frawley"]
        headline = "No consensus - high uncertainty; leaning toward Frawley's verdict by default" \
            if "frawley" in v else "No consensus - high uncertainty"
    # disagreement analysis
    analysis = []
    if len(set(v.values())) > 1:
        if f:
            analysis.append("This match has a clear favourite, so Frawley's event chart is the most decisive method.")
        if k and k["d9_cusp_planet"]:
            analysis.append("Planets sit on the D9 cusps, so Chokoisky's verdict is regarded as highly reliable.")
        if r and r["saturn_8th"]:
            analysis.append("Rao's interruption indicator is active: weight Chokoisky and Frawley more.")
    # confidence (8.2.4, before the ML multiplier which is applied by the web layer)
    conf = {3: 40, 2: 25}.get(agree, 10)
    strong_flags = []
    if r and abs(r["diff"]) > 8 and v.get("rao") == winner:
        conf += 10
        strong_flags.append("Rao margin > 8")
    if k and abs(k["total"]) > 9 and v.get("chokoisky") == winner:
        conf += 10
        strong_flags.append("Chokoisky total beyond ±9")
    if f and f["strong_count"] >= 2 and v.get("frawley") == winner:
        conf += 10
        strong_flags.append("Frawley: 2+ strong testimonies")
    if k and k["d9_cusp_planet"]:
        conf += 8
    if k and k["sky"]:
        conf += 5
    if f and (f["lord1_on_7th"] or f["lord7_on_1st"]):
        conf += 7
    conf -= 15 * bool(s.get("any")) + 15 * bool(r and r["saturn_8th"])
    conf = max(0, min(100, conf))
    # goal ranges -> intersection of each agreeing engine's winning-margin range
    ranges = []
    if r and v.get("rao") == winner:
        a_, b_ = r["goal_diff_range"]
        ranges.append((max(1, a_), max(1, b_)))
    if k and v.get("chokoisky") == winner:
        g = max(1, k["goal_diff"])
        ranges.append((max(1, g - 1), g + 1))
    if f and v.get("frawley") == winner:
        g = max(1, f["goals"]["winner"] - f["goals"]["loser"])
        ranges.append((max(1, g - 1), g))
    if winner == "draw":
        likely, plausible = "1–1", "0–0 to 2–2"
    else:
        lo = max([a_ for a_, _ in ranges] or [1])
        hi = min([b_ for _, b_ in ranges] or [2])
        if lo > hi:                                       # no overlap: fall back to the union
            lo, hi = min(a_ for a_, _ in ranges), max(b_ for _, b_ in ranges)
        hi = min(hi, 4)                                   # margins > 4 goals are statistically rare
        lo = min(lo, hi)
        wg = max(lo, f["goals"]["winner"] if f and v.get("frawley") == winner else lo)
        score = (wg, wg - lo)
        lo_s, hi_s = (lo, 0), (hi + 1, 1)
        if winner == "B":
            score, lo_s, hi_s = score[::-1], lo_s[::-1], hi_s[::-1]
        likely = f"{score[0]}–{score[1]}"
        plausible = f"{lo_s[0]}–{lo_s[1]} to {hi_s[0]}–{hi_s[1]}"
    obs = []
    margins_small = (not r or abs(r["diff"]) <= 3) and (not k or abs(k["total"]) <= 6) and (not f or abs(f["score"]) <= 1.5)
    if inp.get("draw_possible") and margins_small:
        obs.append("Likely drawn match - all engines show a narrow margin")
    if k:
        obs.append("Likely high-scoring" if abs(k["total"]) >= 15 else
                   ("Likely low-scoring" if abs(k["total"]) <= 4 else "Moderate scoring expected"))
    if f and f["late_goal"]:
        obs.append("Late winning goal indicated - the Moon's final aspect completes late in its range")
    if r and r["saturn_8th"]:
        obs.append("Saturn-on-8th caveat - potential interruption (weather, crowd, technical)")
    if s.get("eclipse_window") or s.get("station"):
        obs.append("Sandhi window active - weather/disruption (D/L) risk")
    if r and r["planetary_influence_included"]:
        jf, ju = r["fav"].get("planetary_influence"), r["und"].get("planetary_influence")
        if jf is not None and ju is not None and jf != ju:
            obs.append(f"Captain/jersey influence favours {team_name(fav_side if jf > ju else ('B' if fav_side == 'A' else 'A'))}")
        if inp.get("color_fav") and inp.get("color_fav") == inp.get("color_und"):
            obs.append("Jersey colour clash - both sides share the same planetary colour")
    if k and (k["nama_pada_fav"] or k["nama_pada_und"]):
        obs.append(f"Nama pada: MC syllable '{k['mc_syllable']}' matches "
                   f"{team_name(fav_side) if k['nama_pada_fav'] else team_name('B' if fav_side == 'A' else 'A')}")
    if k and k["planetary_war_winner"]:
        obs.append(f"Planetary war won by the {'favourite' if k['planetary_war_winner'] == 'fav' else 'underdog'}'s significator")
    if v:
        pattern = ("all_agree" if len(v) == 3 and len(set(v.values())) == 1 else
                   "rao_chokoisky_agree" if v.get("rao") == v.get("chokoisky") else
                   "rao_frawley_agree" if "frawley" in v and v.get("rao") == v.get("frawley") else
                   "chokoisky_frawley_agree" if "frawley" in v and v.get("chokoisky") == v.get("frawley") else
                   "all_disagree")
    else:
        pattern = "all_disagree"
    return {"winner": winner, "headline": headline, "agreement": agree, "pattern": pattern, "verdicts": v,
            "engine_weights": w, "disagreement_analysis": analysis, "base_confidence": conf,
            "strong_flags": strong_flags, "goal_range": {"likely": likely, "plausible": plausible},
            "observations": obs}
