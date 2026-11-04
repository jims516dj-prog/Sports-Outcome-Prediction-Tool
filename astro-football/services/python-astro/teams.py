"""Club names, home-ground coordinates and timezones (shared by data sync)."""

ALIASES = {
    # Germany
    "1. FC Heidenheim 1846": "Heidenheim", "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "FC Bayern München": "Bayern München", "Bor. Mönchengladbach": "Borussia Mönchengladbach",
    "FC St. Pauli 1910": "FC St. Pauli", "SpVgg Greuther Fürth 1903": "SpVgg Greuther Fürth",
    "TSG 1899 Hoffenheim": "1899 Hoffenheim", "SV Werder Bremen": "Werder Bremen",
    # Spain
    "Club Atlético de Madrid": "Atlético Madrid", "Deportivo Alavés": "CD Alavés",
    "RCD Espanyol de Barcelona": "Espanyol Barcelona", "RC Celta de Vigo": "RC Celta",
    "Rayo Vallecano de Madrid": "Rayo Vallecano", "Real Betis Balompié": "Real Betis",
    "Real Madrid CF": "Real Madrid", "Real Sociedad de Fútbol": "Real Sociedad",
    "Real Valladolid CF": "Real Valladolid",
    # Italy
    "Atalanta BC": "Atalanta", "Bologna FC 1909": "Bologna FC", "Hellas Verona FC": "Hellas Verona",
    "FC Internazionale Milano": "Inter", "Juventus FC": "Juventus", "SS Lazio": "Lazio Roma",
    "Parma FC": "Parma Calcio 1913", "UC Sampdoria": "Sampdoria", "US Sassuolo Calcio": "Sassuolo Calcio",
    # France
    "AS Monaco FC": "AS Monaco", "Olympique de Marseille": "Olympique Marseille",
    "Paris Saint-Germain FC": "Paris Saint-Germain", "Racing Club de Lens": "RC Lens",
    "RC Strasbourg Alsace": "RC Strasbourg", "Stade Rennais FC 1901": "Stade Rennais",
}


def canon(name: str, league: str) -> str:
    n = ALIASES.get(name, name)
    if league.startswith("en."):
        for suf in (" AFC", " FC"):
            if n.endswith(suf):
                n = n[: -len(suf)]
        n = {"Bournemouth": "AFC Bournemouth"}.get(n, n)
    return n


COORDS = {
    # England
    "AFC Bournemouth": (50.735, -1.838), "Arsenal": (51.555, -0.108), "Aston Villa": (52.509, -1.885),
    "Birmingham City": (52.476, -1.868), "Blackburn Rovers": (53.729, -2.489), "Blackpool": (53.805, -3.048),
    "Bolton Wanderers": (53.581, -2.536), "Brentford": (51.491, -0.289), "Brighton & Hove Albion": (50.862, -0.083),
    "Burnley": (53.789, -2.230), "Cardiff City": (51.473, -3.203), "Chelsea": (51.482, -0.191),
    "Crystal Palace": (51.398, -0.086), "Everton": (53.439, -2.966), "Fulham": (51.475, -0.222),
    "Huddersfield Town": (53.654, -1.768), "Hull City": (53.746, -0.368), "Ipswich Town": (52.055, 1.145),
    "Leeds United": (53.778, -1.572), "Leicester City": (52.620, -1.142), "Liverpool": (53.431, -2.961),
    "Luton Town": (51.884, -0.432), "Manchester City": (53.483, -2.200), "Manchester United": (53.463, -2.291),
    "Middlesbrough": (54.578, -1.217), "Newcastle United": (54.976, -1.622), "Norwich City": (52.622, 1.309),
    "Nottingham Forest": (52.940, -1.133), "Queens Park Rangers": (51.509, -0.232), "Reading": (51.422, -0.983),
    "Sheffield United": (53.370, -1.471), "Southampton": (50.906, -1.391), "Stoke City": (52.988, -2.176),
    "Sunderland": (54.915, -1.388), "Swansea City": (51.643, -3.935), "Tottenham Hotspur": (51.604, -0.066),
    "Watford": (51.650, -0.402), "West Bromwich Albion": (52.509, -1.964), "West Ham United": (51.539, -0.017),
    "Wigan Athletic": (53.548, -2.654), "Wolverhampton Wanderers": (52.590, -2.130),
    # Germany
    "Heidenheim": (48.669, 10.139), "1. FC Kaiserslautern": (49.434, 7.776), "1. FC Köln": (50.933, 6.875),
    "1. FC Nürnberg": (49.426, 11.126), "1. FC Union Berlin": (52.457, 13.568), "1. FSV Mainz 05": (49.984, 8.224),
    "1899 Hoffenheim": (49.239, 8.888), "Arminia Bielefeld": (52.032, 8.517), "Bayer Leverkusen": (51.038, 7.002),
    "Bayern München": (48.219, 11.625), "Borussia Mönchengladbach": (51.175, 6.385),
    "Borussia Dortmund": (51.493, 7.452), "Eintracht Braunschweig": (52.290, 10.521),
    "Eintracht Frankfurt": (50.069, 8.646), "FC Augsburg": (48.323, 10.886), "FC Ingolstadt 04": (48.746, 11.486),
    "FC Schalke 04": (51.555, 7.068), "FC St. Pauli": (53.555, 9.968), "Fortuna Düsseldorf": (51.262, 6.733),
    "Hamburger SV": (53.587, 9.899), "Hannover 96": (52.360, 9.731), "Hertha BSC": (52.515, 13.239),
    "Holstein Kiel": (54.349, 10.124), "RB Leipzig": (51.346, 12.348), "SC Freiburg": (48.022, 7.830),
    "SC Paderborn 07": (51.731, 8.711), "SV Darmstadt 98": (49.858, 8.672), "Werder Bremen": (53.066, 8.838),
    "SpVgg Greuther Fürth": (49.487, 10.999), "VfB Stuttgart": (48.792, 9.232), "VfL Bochum 1848": (51.490, 7.236),
    "VfL Wolfsburg": (52.432, 10.804),
    # Spain
    "Athletic Club": (43.264, -2.949), "Atlético Madrid": (40.436, -3.600), "CA Osasuna": (42.797, -1.637),
    "CD Alavés": (42.837, -2.688), "CD Leganés": (40.340, -3.760), "Cádiz CF": (36.503, -6.273),
    "Córdoba CF": (37.872, -4.765), "Deportivo La Coruña": (43.369, -8.417), "Elche CF": (38.267, -0.663),
    "Espanyol Barcelona": (41.348, 2.076), "FC Barcelona": (41.381, 2.123), "Getafe CF": (40.326, -3.715),
    "Girona FC": (41.961, 2.829), "Granada CF": (37.153, -3.596), "Levante UD": (39.495, -0.364),
    "Málaga CF": (36.734, -4.426), "RC Celta": (42.212, -8.740), "RCD Mallorca": (39.590, 2.630),
    "Rayo Vallecano": (40.392, -3.659), "Real Betis": (37.357, -5.982), "Real Madrid": (40.453, -3.688),
    "Real Sociedad": (43.301, -1.974), "Real Valladolid": (41.645, -4.761), "Real Zaragoza": (41.637, -0.902),
    "SD Eibar": (43.182, -2.476), "SD Huesca": (42.131, -0.418), "Sevilla FC": (37.384, -5.971),
    "Sporting Gijón": (43.536, -5.637), "UD Almería": (36.840, -2.436), "UD Las Palmas": (28.100, -15.457),
    "Valencia CF": (39.475, -0.358), "Villarreal CF": (39.944, -0.104),
    # Italy
    "AC Cesena": (44.140, 12.250), "AC Milan": (45.478, 9.124), "Inter": (45.478, 9.124), "AC Monza": (45.582, 9.308),
    "ACF Fiorentina": (43.781, 11.282), "AS Livorno": (43.535, 10.303), "AS Roma": (41.934, 12.455),
    "Lazio Roma": (41.934, 12.455), "Atalanta": (45.709, 9.681), "Benevento Calcio": (41.131, 14.784),
    "Bologna FC": (44.492, 11.310), "Brescia Calcio": (45.570, 10.235), "Cagliari Calcio": (39.200, 9.137),
    "Calcio Catania": (37.516, 15.071), "Carpi FC": (44.785, 10.885), "Chievo Verona": (45.435, 10.969),
    "Hellas Verona": (45.435, 10.969), "Como 1907": (45.814, 9.072), "Delfino Pescara": (42.452, 14.229),
    "Empoli FC": (43.727, 10.955), "FC Crotone": (39.080, 17.126), "Frosinone Calcio": (41.627, 13.330),
    "Genoa CFC": (44.416, 8.952), "Sampdoria": (44.416, 8.952), "Juventus": (45.110, 7.641),
    "SSC Napoli": (40.828, 14.193), "Parma Calcio 1913": (44.795, 10.338), "SPAL 2013 Ferrara": (44.841, 11.606),
    "Sassuolo Calcio": (44.715, 10.649), "Spezia Calcio": (44.102, 9.808), "Torino FC": (45.042, 7.650),
    "US Cremonese": (45.139, 10.030), "US Lecce": (40.365, 18.209), "US Palermo": (38.153, 13.342),
    "US Salernitana 1919": (40.646, 14.824), "Udinese Calcio": (46.082, 13.200), "Venezia FC": (45.428, 12.364),
    # France
    "AC Ajaccio": (41.931, 8.776), "Gazélec FC Ajaccio": (41.927, 8.737), "AJ Auxerre": (47.787, 3.589),
    "AS Monaco": (43.727, 7.416), "AS Nancy Lorraine": (48.695, 6.211), "AS Saint-Étienne": (45.461, 4.390),
    "Amiens SC": (49.894, 2.264), "Angers SCO": (47.460, -0.531), "Clermont Foot 63": (45.816, 3.121),
    "Dijon FCO": (47.325, 5.068), "EA Guingamp": (48.566, -3.164), "ESTAC Troyes": (48.307, 4.099),
    "FC Lorient": (47.749, -3.369), "FC Metz": (49.110, 6.159), "FC Nantes": (47.256, -1.525),
    "Girondins Bordeaux": (44.897, -0.561), "Le Havre AC": (49.499, 0.170), "Lille OSC": (50.612, 3.130),
    "Montpellier HSC": (43.622, 3.812), "Nîmes Olympique": (43.816, 4.360), "OGC Nice": (43.705, 7.193),
    "Olympique Lyonnais": (45.765, 4.982), "Olympique Marseille": (43.270, 5.396),
    "Paris Saint-Germain": (48.841, 2.253), "RC Lens": (50.433, 2.815), "RC Strasbourg": (48.560, 7.755),
    "SC Bastia": (42.651, 9.443), "SM Caen": (49.180, -0.397), "Stade Brestois 29": (48.403, -4.462),
    "Stade Rennais": (48.108, -1.713), "Stade de Reims": (49.247, 4.025), "Toulouse FC": (43.583, 1.434),
    "Évian Thonon Gaillard": (45.892, 6.118),
}

LEAGUE_TZ = {"en.1": "Europe/London", "de.1": "Europe/Berlin", "es.1": "Europe/Madrid",
             "it.1": "Europe/Rome", "fr.1": "Europe/Paris"}
TEAM_TZ = {"UD Las Palmas": "Atlantic/Canary"}


# ---------------------------------------------------------------- added for data sync
ALIASES.update({
    "RC Deportivo La Coruña": "Deportivo La Coruña", "ES Troyes AC": "ESTAC Troyes",
    "Sport Lisboa e Benfica": "Benfica", "SL Benfica": "Benfica", "AFC Ajax": "Ajax",
    "Sporting CP": "Sporting Clube de Portugal", "SC Braga": "Sporting Clube de Braga",
    "LOSC Lille": "Lille OSC", "Feyenoord": "Feyenoord Rotterdam", "PSV Eindhoven": "PSV", "NEC Nijmegen": "NEC",
    "FC Twente": "FC Twente '65", "Real Racing Club": "Real Racing Club de Santander",
})
COORDS.update({
    # England (Championship and newly promoted)
    "Bristol City": (51.440, -2.620), "Charlton Athletic": (51.486, 0.036), "Coventry City": (52.448, -1.496),
    "Derby County": (52.915, -1.447), "Lincoln City": (53.218, -0.541), "Millwall": (51.486, -0.051),
    "Oxford United": (51.716, -1.209), "Plymouth Argyle": (50.388, -4.151), "Portsmouth": (50.796, -1.064),
    "Preston North End": (53.772, -2.688), "Sheffield Wednesday": (53.411, -1.501), "Wrexham": (53.052, -3.004),
    # Spain, Italy, France, Germany (newly promoted)
    "Real Oviedo": (43.360, -5.870), "Real Racing Club de Santander": (43.476, -3.789), "AC Pisa 1909": (43.725, 10.399),
    "Le Mans FC": (47.958, 0.224), "Paris FC": (48.843, 2.253), "SV 07 Elversberg": (49.317, 7.125),
    # Netherlands
    "Ajax": (52.314, 4.942), "AZ": (52.613, 4.743), "Almere City FC": (52.375, 5.276), "FC Groningen": (53.205, 6.592),
    "FC Twente '65": (52.237, 6.837), "FC Utrecht": (52.078, 5.146), "FC Volendam": (52.494, 5.071),
    "Feyenoord Rotterdam": (51.894, 4.523), "Fortuna Sittard": (51.000, 5.865), "Go Ahead Eagles": (52.252, 6.168),
    "Heracles Almelo": (52.344, 6.664), "NAC Breda": (51.574, 4.749), "NEC": (51.829, 5.863), "PEC Zwolle": (52.500, 6.075),
    "PSV": (51.442, 5.467), "RKC Waalwijk": (51.687, 5.061), "SBV Excelsior": (51.918, 4.517),
    "SC Cambuur-Leeuwarden": (53.191, 5.807), "SC Heerenveen": (52.958, 5.940), "Sparta Rotterdam": (51.920, 4.433),
    "Telstar 1963": (52.462, 4.632), "Willem II Tilburg": (51.546, 5.073), "ADO Den Haag": (52.062, 4.383),
    # Portugal
    "AVS": (41.370, -8.410), "Académico de Viseu FC": (40.661, -7.913), "Boavista FC": (41.162, -8.643),
    "CD Nacional": (32.665, -16.900), "CD Santa Clara": (37.746, -25.666), "CD Tondela": (40.517, -8.083),
    "CF Estrela da Amadora": (38.756, -9.234), "CS Marítimo": (32.646, -16.926), "Casa Pia AC": (38.760, -9.200),
    "FC Alverca": (38.897, -9.040), "FC Arouca": (40.931, -8.245), "FC Famalicão": (41.405, -8.522),
    "FC Porto": (41.162, -8.584), "GD Estoril Praia": (38.707, -9.398), "Gil Vicente FC": (41.548, -8.611),
    "Moreirense FC": (41.379, -8.354), "Rio Ave FC": (41.364, -8.742), "SC Farense": (37.019, -7.932),
    "Benfica": (38.753, -9.185), "Sporting Clube de Braga": (41.563, -8.430),
    "Sporting Clube de Portugal": (38.761, -9.161), "Vitória Guimarães": (41.446, -8.301),
    # clubs from earlier seasons
    "Barnsley": (53.552, -1.468), "Milton Keynes Dons": (52.010, -0.734), "Peterborough United": (52.565, -0.240),
    "Rotherham United": (53.428, -1.362), "Wycombe Wanderers": (51.630, -0.800), "De Graafschap": (51.966, 6.290),
    "FC Emmen": (52.781, 6.902), "Vitesse": (51.963, 5.893), "VVV-Venlo": (51.360, 6.149),
    "Belenenses SAD": (38.709, -9.261), "CD Aves": (41.370, -8.410), "CD Feirense": (40.926, -8.541),
    "FC Vizela": (41.373, -8.307), "GD Chaves": (41.746, -7.470), "Paços de Ferreira": (41.276, -8.384),
    "Portimonense SC": (37.136, -8.540), "Vitória Setúbal": (38.528, -8.885),
})
ALIASES.update({"SBV Vitesse": "Vitesse"})
LEAGUE_TZ.update({"en.2": "Europe/London", "nl.1": "Europe/Amsterdam", "pt.1": "Europe/Lisbon"})
TEAM_TZ.update({"CD Santa Clara": "Atlantic/Azores", "CD Nacional": "Atlantic/Madeira", "CS Marítimo": "Atlantic/Madeira"})
