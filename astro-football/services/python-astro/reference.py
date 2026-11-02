"""Reference tables (spec sections 4 and 11.3).

The cited book tables were not available when this was built. Where a page is cited,
the standard classical table is used instead and labelled as such; every table is
shown on the Settings page so it can be checked against the books.
"""

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
         "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Ma", "Ve", "Me", "Mo", "Su", "Me", "Ve", "Ma", "Ju", "Sa", "Sa", "Ju"]
PLANET_ORDER = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke", "Ur", "Ne", "Pl", "Ce", "Ch", "Uk", "Gu"]
PLANET_NAMES = {"Su": "Sun", "Mo": "Moon", "Ma": "Mars", "Me": "Mercury", "Ju": "Jupiter", "Ve": "Venus",
                "Sa": "Saturn", "Ra": "Rahu", "Ke": "Ketu", "Ur": "Uranus", "Ne": "Neptune", "Pl": "Pluto",
                "Ce": "Ceres", "Ch": "Chiron", "Uk": "Upaketu", "Gu": "Gulika"}
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya",
              "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
              "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
VIM = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
VIM_YEARS = {"Ke": 7, "Ve": 20, "Su": 6, "Mo": 10, "Ma": 7, "Ra": 18, "Ju": 16, "Sa": 19, "Me": 17}

# Dignities (classical; stands in for Chokoisky table 3.1, p.46)
EXALT = {"Su": 0, "Mo": 1, "Ma": 9, "Me": 5, "Ju": 3, "Ve": 11, "Sa": 6, "Ra": 1, "Ke": 7}
DEBIL = {p: (s + 6) % 12 for p, s in EXALT.items()}
OWN = {"Su": {4}, "Mo": {3}, "Ma": {0, 7}, "Me": {2, 5}, "Ju": {8, 11}, "Ve": {1, 6}, "Sa": {9, 10}}
DIG_BALA_HOUSE = {"Ju": 1, "Me": 1, "Su": 10, "Ma": 10, "Sa": 7, "Mo": 4, "Ve": 4}


def dignity(p, sign):
    if p in EXALT and EXALT[p] == sign:
        return 2
    if p in OWN and sign in OWN[p]:
        return 1
    if p in DEBIL and DEBIL[p] == sign:
        return -1
    return 0


# Natural friendships (Parashari; stands in for Rao p.39)
FRIENDS = {"Su": {"Mo", "Ma", "Ju"}, "Mo": {"Su", "Me"}, "Ma": {"Su", "Mo", "Ju"}, "Me": {"Su", "Ve"},
           "Ju": {"Su", "Mo", "Ma"}, "Ve": {"Me", "Sa"}, "Sa": {"Me", "Ve"}, "Ra": {"Me", "Ve", "Sa"},
           "Ke": {"Ma", "Ju"}}
ENEMIES = {"Su": {"Ve", "Sa"}, "Mo": set(), "Ma": {"Me"}, "Me": {"Mo"}, "Ju": {"Me", "Ve"},
           "Ve": {"Su", "Mo"}, "Sa": {"Su", "Mo", "Ma"}, "Ra": {"Su", "Mo", "Ma"}, "Ke": {"Su", "Mo"}}


def relation(a, b):
    if a == b:
        return 1
    if a not in FRIENDS:
        return 0
    return 1 if b in FRIENDS[a] else (-1 if b in ENEMIES[a] else 0)


def friendship_matrix():
    g = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
    lab = {1: "Friend", 0: "Neutral", -1: "Enemy"}
    return {a: {b: ("Self" if a == b else lab[relation(a, b)]) for b in g} for a in g}


# Rao planetary influence (spec 5.3 step 3)
NUMBER_PLANET = {1: "Su", 2: "Mo", 3: "Ju", 4: "Ra", 5: "Me", 6: "Ve", 7: "Ke", 8: "Sa", 9: "Ma"}
COLOR_PLANET = {"Sun-maroon": "Su", "Moon-white": "Mo", "Mars-red": "Ma", "Mercury-green": "Me",
                "Jupiter-gold": "Ju", "Venus-yellow": "Ve", "Saturn-black/blue": "Sa",
                "Rahu-brown": "Ra", "Ketu-grey": "Ke"}
JERSEY_QUALITY = {9: 1.0, 7: 1.0, 3: 0.5, 5: 0.5, 1: 0.5, 8: -1.0, 4: -1.0, 2: -1.0, 6: 0.0}


def reduce_digit(n: int) -> int:
    n = abs(int(n))
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n or 9


# 108 navamsha (nakshatra-pada) syllables - Avakahada chakra; stands in for Chokoisky table 7.1
PADA_SYLLABLES = (
    "chu che cho la  li lu le lo  a i u e  o va vi vu  ve vo ka ki  ku gha nga chha  "
    "ke ko ha hi  hu he ho da  di du de do  ma mi mu me  mo ta ti tu  te to pa pi  "
    "pu sha na tha  pe po ra ri  ru re ro ta  ti tu te to  na ni nu ne  no ya yi yu  "
    "ye yo ba bi  bu dha pha dha  be bo ja ji  ju je jo gha  ga gi gu ge  go sa si su  "
    "se so da di  du tha jha na  de do cha chi").split()
assert len(PADA_SYLLABLES) == 108

# Nakshatra yogataras (28 incl. Abhijit). Positions are computed live from the Swiss
# Ephemeris star catalogue; effects only where the specification states one.
YOGATARAS = [("Ashwini", "Sheratan"), ("Bharani", "41 Ari"), ("Krittika", "Alcyone"), ("Rohini", "Aldebaran"),
             ("Mrigashira", "Meissa"), ("Ardra", "Betelgeuse"), ("Punarvasu", "Pollux"), ("Pushya", "Asellus Australis"),
             ("Ashlesha", "Minchir"), ("Magha", "Regulus"), ("Purva Phalguni", "Zosma"), ("Uttara Phalguni", "Denebola"),
             ("Hasta", "Algorab"), ("Chitra", "Spica"), ("Swati", "Arcturus"), ("Vishakha", "Zubenelgenubi"),
             ("Anuradha", "Dschubba"), ("Jyeshtha", "Antares"), ("Mula", "Shaula"), ("Purva Ashadha", "Kaus Media"),
             ("Uttara Ashadha", "Nunki"), ("Abhijit", "Vega"), ("Shravana", "Altair"), ("Dhanishta", "Rotanev"),
             ("Shatabhisha", "Hydor"), ("Purva Bhadrapada", "Markab"), ("Uttara Bhadrapada", "Algenib"),
             ("Revati", "Revati")]
# key stars from the spec: (spec sidereal longitude used as fallback, effect points, meaning)
KEY_STARS = {"Regulus": (126.0, 7, "strong victory (kingly)"), "Pollux": (89.5, 7, "strong victory (full quiver)"),
             "Vega": (261.5, 7, "victory ('the victorious')"), "Spica": (179.92, -7, "loss when on a cusp"),
             "Antares": (226.0, 0, "largely nullified by Aldebaran opposite"),
             "Algol": (56.0, -4, "moderate negative (beheading/loss)"), "Wasat": (85.0, -4, "behaves like Saturn"),
             "Hyadum I": (42.0, 3, "Hyades - mild positive")}

# Chokoisky table 4.1 (D1 cusps): effect on (1/7, 4/10, 6/12)
D1_EFFECT = {"Su": (-1, -1, -1), "Mo": (-1, -1, -1), "Ma": (1, -1, 1), "Ra": (1, 1, 1), "Ju": (1, 1, 1),
             "Sa": (-1, 1, 1), "Me": ("M", "M", 1), "Ke": (-1, -1, -1), "Ve": (1, 1, 1),
             "Ur": ("UR", "UR", "UR"), "Ne": ("NE", "NE", "NE"), "Pl": (-1, 1, -1), "Uk": (-1, -1, -1),
             "Gu": (-1, 1, 0), "Ch": (0, 0, 0), "Ce": (0, 0, 0)}
# Chokoisky table 5.3 (D9 1/7 cusps) - Mars, Mercury, Venus opposite to D1
D9_EFFECT = {"Su": -1, "Mo": -1, "Ma": -1, "Ra": 1, "Ju": 1, "Sa": -1, "Me": 1, "Ke": -1, "Ve": -1,
             "Ur": "UR", "Ne": "NE", "Pl": -1, "Uk": -1, "Gu": -1, "Ch": 0, "Ce": 0}
D9_MEANING = {"Su": "cautious, low-scoring", "Mo": "lazy, unstable", "Ma": "frustration, self-undoing",
              "Ra": "ambition", "Ju": "luck, optimism", "Sa": "depression, slowness", "Me": "skill, speed",
              "Ke": "confusion", "Ve": "complacency", "Ur": "electric", "Ne": "inspiration when Rx",
              "Pl": "heaviness", "Uk": "like Ketu", "Gu": "defeat", "Ch": "no effect assigned",
              "Ce": "no effect assigned"}
INVISIBLE = {"Ra", "Ke", "Ur", "Ne", "Pl", "Ce", "Ch", "Uk", "Gu"}
MALEFICS = {"Su", "Ma", "Sa", "Ra", "Ke"}
BENEFICS = {"Ju", "Ve", "Me", "Mo"}
BRIGHTNESS = ["Ve", "Ju", "Ma", "Me", "Sa"]

# Mean daily motion (deg/day) - a planet below 10% of this is treated as stationary
MEAN_SPEED = {"Me": 1.383, "Ve": 1.2, "Ma": 0.524, "Ju": 0.083, "Sa": 0.033}

ANTISCIA_PAIRS = [("Aries", "Virgo"), ("Taurus", "Leo"), ("Gemini", "Cancer"), ("Libra", "Pisces"),
                  ("Scorpio", "Sagittarius"), ("Capricorn", "Aquarius")]
ARABIAN_PARTS = {"Fortuna": "Asc + Moon - Sun (not reversed at night)",
                 "Resignation": "Saturn + Jupiter - Sun"}

SPORT_PRESETS = {
    "football": {"label": "Football / Soccer", "draw_contexts": ["league", "friendly"],
                 "moon_range_deg": 5.0, "extra_time_deg": 1.0, "goal_divisor": 3.0},
    "american_football": {"label": "American Football", "draw_contexts": [], "moon_range_deg": 5.0,
                          "extra_time_deg": 1.0, "goal_divisor": 1.0},
    "cricket": {"label": "Cricket", "draw_contexts": ["league"], "moon_range_deg": 5.0,
                "extra_time_deg": 0.0, "goal_divisor": 1.0},
    "tennis": {"label": "Tennis", "draw_contexts": [], "moon_range_deg": 5.0, "extra_time_deg": 0.0,
               "goal_divisor": 3.0},
    "basketball": {"label": "Basketball", "draw_contexts": [], "moon_range_deg": 5.0, "extra_time_deg": 0.5,
                   "goal_divisor": 1.0},
    "ice_hockey": {"label": "Ice Hockey", "draw_contexts": [], "moon_range_deg": 5.0, "extra_time_deg": 1.0,
                   "goal_divisor": 3.0},
}

DEFAULT_TOGGLES = {
    "engines": {"rao": True, "chokoisky": True, "frawley": True},
    "rao": {"nation_charts": True, "planetary_influence": True},
    "chokoisky": {"victory_houses": True, "sky_pky": True, "d1_cusps": True, "d9_cusps": True,
                  "nama_pada": True, "sublords": True, "nakshatra_tara": True, "planetary_war": True},
    "frawley": {"house_placement": True, "antiscia": True, "moon_placement": True, "fortuna": True,
                "moon_aspects": True, "dispositor": True, "misc": True},
}

AYANAMSHA_DEFAULTS = {"rao": "lahiri", "chokoisky": "lahiri", "chokoisky_sublords": "krishnamurti",
                      "frawley": "tropical"}


def all_tables():
    return {"friendships_rao_p39_standard_parashari": friendship_matrix(),
            "d1_cusp_effects_chokoisky_t4_1": D1_EFFECT, "d9_effects_chokoisky_t5_3": D9_EFFECT,
            "d9_meanings": D9_MEANING,
            "navamsha_syllables_avakahada": [{"nakshatra": NAKSHATRAS[i // 4], "pada": i % 4 + 1,
                                              "syllable": s} for i, s in enumerate(PADA_SYLLABLES)],
            "yogataras": YOGATARAS, "key_stars": KEY_STARS,
            "dignities": {"exaltation": EXALT, "debilitation": DEBIL, "own": {k: sorted(v) for k, v in OWN.items()},
                          "dig_bala_house": DIG_BALA_HOUSE},
            "station_speeds": MEAN_SPEED, "antiscia_pairs": ANTISCIA_PAIRS, "arabian_parts": ARABIAN_PARTS,
            "number_planet": NUMBER_PLANET, "color_planet": COLOR_PLANET, "jersey_quality": JERSEY_QUALITY,
            "sport_presets": SPORT_PRESETS, "ayanamsha_defaults": AYANAMSHA_DEFAULTS, "signs": SIGNS,
            "sign_lords": SIGN_LORD}
