# Astrological Football Match Analyzer — Build Specification Prompt

> **Paste this entire document into your LLM coding agent (ChatGPT, Claude, Cursor, etc.) to generate the complete web application. This is the single source-of-truth specification.**

---

## 0. How to Use This Prompt

You are building a Next.js 16 web application that performs astrological analysis of football (soccer) matches using **three distinct methodologies** drawn from three reference books. Each methodology runs as an independent analysis engine. The three engine outputs are then reconciled into a comparative outlook.

Beyond the three engines, the app also functions as a **living research instrument**: users can add historical matches (with final scorelines), add new matches that get analyzed and later edited with the actual result, and a machine-learning subsystem continuously mines the growing dataset to discover which astrological combinations most strongly correlate with correct predictions — feeding those weights back into the engines to improve future predictions.

The three reference books (treat them as authoritative source material):

1. **"Sports Astrology: The Inclusive Methodology of Game Analysis"** by Dr. Ravi Rao (2017) — Vedic, sidereal, nations-chart + planetary-influence method.
2. **"Gambler's Dharma: Sports Betting with Vedic Astrology"** by Simon Chokoisky (2017) — Vedic, sidereal (Lahiri + Krishnamurti), multi-tier point system with navamsha + sublords.
3. **"Sports Astrology"** by John Frawley (Apprentice Books, 2007) — Western/traditional, event-chart method with Placidus houses.

Build the app so that all three engines share a single match-setup form and chart-computation backend, then each runs its own analysis layer and emits its own verdict. The UI presents the three verdicts side-by-side in a comparative table plus a synthesized outlook. After every analyzed match (and every historical match entered), the dataset grows; a nightly ML job recomputes combination weights that feed back into the synthesis layer.

**Non-negotiable deliverables:**

- A match-setup form capturing all inputs (4 mandatory + others optional per user toggle).
- A backend that computes Vedic astrological charts (Rashi + Navamsha) and Western event charts.
- Three independent analysis engines implementing Rao, Chokoisky, and Frawley methodologies exactly as specified in §5, §6, §7.
- A results page showing each engine's verdict, a comparative table, and the synthesized outlook per §8.
- A **historical dataset** with the ability to add old matches (with final scorelines), add new matches (which get analyzed and then later edited with the actual scoreline), and browse/search the full dataset.
- A **machine-learning subsystem** that mines the dataset to find the strongest predictive astrological combinations over time and feeds those weights back into the synthesis layer (detailed in §12).
- A persistent anti-betting disclaimer banner per §10.

---

## 1. Project Overview

The app has **four functional surfaces**:

1. **Analyze** — enter a match, get three-engine analysis + synthesized outlook, save the match to the historical dataset with status `pending`. After the match is played, the user edits the record to add the actual scoreline; the record status becomes `completed`.
2. **Historical Dataset** — browse, search, filter, add, edit, and export the full record of matches (old + new). Each record carries teams, odds, scoreline (or null), date, venue, kickoff time, captain/jersey data (if entered), chart snapshots, and engine verdicts.
3. **ML Training Dashboard** — view the ML model's discovered combination weights, retrain on demand, see accuracy metrics per engine and per combination, rollback to previous model versions.
4. **Settings** — manage the reference data tables (team founding charts, venue coordinates, sport presets, ayanamsha defaults) and toggle which engines/techniques are active.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui | Modern, fast, good DX |
| Backend | Next.js API routes for orchestration + a Python FastAPI microservice for heavy astrology math | Swiss Ephemeris is best in Python |
| Astrology engine | `pyswisseph` (Swiss Ephemeris Python binding) | Gold standard, all planets + asteroids + cusps |
| Charts library | `kerykeion` (Vedic helper) or pure `pyswisseph` | Both work; kerykeion faster to bootstrap |
| **Stadium geocoding** | **Wikipedia REST API** (`https://en.wikipedia.org/w/api.php` with `action=query&prop=coordinates&titles=...`) for primary lookup, **Nominatim (OpenStreetMap)** as fallback, **manual lat/long entry** as final override | Wikipedia is authoritative for stadium coordinates (each stadium article typically has geo coordinates); manual override is mandatory per user requirement |
| Timezone | `tzfpy` or `timezonefinder` + `pytz` | Convert GMT to local at venue lat/long |
| Database | **PostgreSQL via Prisma** (upgraded from SQLite — needed for ML feature storage and large dataset) | Relational integrity + JSONB columns for chart snapshots |
| **ML pipeline** | **`scikit-learn`** (Random Forest, Gradient Boosting, Logistic Regression) + **`pandas`** for feature engineering + **`joblib`** for model persistence | Standard, well-documented; no GPU required for tabular feature data |
| **ML scheduling** | **`APScheduler`** (Python) or **BullMQ** (Node) for nightly retraining job | Or trigger on demand from the ML dashboard |
| Chart rendering | `d3.js` or `react-chart-wheel` for the SVG chart wheel | Visualize D1 and D9 |
| Markdown rendering | `react-markdown` | Render analysis text |
| **Search/filter UI** | `tanstack/table` for the historical dataset table | Sortable, filterable, paginated |

**Folder structure:**

```
astro-football/
├── app/
│   ├── page.tsx                      # Home / dashboard
│   ├── analyze/page.tsx              # Match setup form + live analysis
│   ├── dataset/page.tsx              # Historical dataset browser
│   ├── dataset/[id]/page.tsx         # Single match record view + edit
│   ├── dataset/new/page.tsx          # Add historical match (with scoreline)
│   ├── ml/page.tsx                   # ML training dashboard
│   ├── settings/page.tsx             # Reference data management
│   └── api/
│       ├── chart/route.ts            # Compute D1 + D9 from inputs
│       ├── rao/route.ts               # Engine 1
│       ├── chokoisky/route.ts         # Engine 2
│       ├── frawley/route.ts           # Engine 3
│       ├── stadium-lookup/route.ts    # Wikipedia coordinates lookup
│       ├── matches/route.ts           # CRUD for matches
│       └── ml/
│           ├── train/route.ts         # Trigger ML training
│           ├── weights/route.ts        # Get current combination weights
│           └── metrics/route.ts        # Accuracy metrics
├── services/
│   └── python-astro/                  # FastAPI microservice
│       ├── main.py                    # /chart, /sublords, /antiscia, /ml endpoints
│       ├── ml_pipeline.py             # Feature extraction + training
│       ├── wikipedia_geo.py           # Stadium coordinate lookup
│       └── requirements.txt            # pyswisseph, kerykeion, fastapi, tzfpy, scikit-learn, pandas, joblib
├── lib/
│   ├── ml/
│   │   ├── feature_extractor.ts       # Extract features from chart + verdicts
│   │   ├── combination_discoverer.ts  # Find strongest predictive combinations
│   │   └── weights_provider.ts        # Apply learned weights to new analyses
│   └── dataset/
│       └── crud.ts                    # Match record operations
└── prisma/
    └── schema.prisma                  # see §11.1 for full schema
```

---

## 3. Input Form Specification

The match-setup form is the entry point for both **analyzing a new game** and **adding a historical game**. The form has collapsible sections; some are mandatory, others are gated behind toggles.

### 3.1 Core Match Inputs (always required)

| # | Field | Type | Notes |
|---|---|---|---|
| 1 | **Teams playing** | Two text inputs (Team A, Team B) with autocomplete from DB | If known team, autofill founding chart and venue defaults |
| 2 | **Match date** | date picker (`YYYY-MM-DD`) | |
| 3 | **Match time (GMT)** | time picker 24h `HH:MM` | Always entered in GMT; backend auto-converts to local time at the venue. For historical matches, the user can also enter local time + the app auto-converts to GMT. |
| 4 | **Venue name** | text input with autocomplete + lookup button | See §3.2 for the Wikipedia lookup flow |

### 3.2 Stadium / Venue Lookup (NEW per user request)

The venue field has **three layers of resolution**, each overridable:

**Layer 1 — Wikipedia REST API (primary)**

When the user types a venue name and either presses the Lookup button or tabs out of the field:

1. Call `https://en.wikipedia.org/w/api.php?action=query&format=json&prop=coordinates&titles=<venue_name>&redirects=1`
2. Parse the response for the `coordinates` array (most stadium Wikipedia articles have geo coordinates attached).
3. If multiple coordinate entries exist (rare but possible), use the one with `primary: true`.
4. Display the returned lat/long in disabled fields below the venue name with a "From Wikipedia" tag.
5. If Wikipedia has no article or no coordinates attached, fall through to Layer 2.

**Layer 2 — Nominatim (fallback)**

Call `https://nominatim.openstreetmap/search?q=<venue_name>&format=json&limit=1`. Display coordinates with a "From OpenStreetMap" tag. Lower confidence than Wikipedia.

**Layer 3 — Manual override (always available)**

Two enabled lat/long inputs are always shown below the venue name. The user can manually enter or edit coordinates at any time, regardless of what the lookup returned. When the user edits the manual fields, the lookup results are ignored and a "Manual override" tag is shown.

**Implementation note**: persist the venue with its canonical coordinates in the `venues` table on first use, so future matches at the same venue skip the lookup. Include a "last-verified-from" source field (Wikipedia / OpenStreetMap / manual) and a "last-verified-at" timestamp so the user can see how fresh the coordinates are. The Settings page exposes a "Re-verify all venue coordinates from Wikipedia" button.

**UI flow**:

```
[Venue name: _______________] [Lookup] [Save venue to DB]
  ↓ (lookup result)
  Latitude:  [51.5556]   (from Wikipedia)
  Longitude: [-0.1083]   (from Wikipedia)
  [✏️ Edit manually]
  ↓ (after edit)
  Latitude:  [51.5550]   (manual override)
  Longitude: [-0.1089]   (manual override)
```

### 3.3 Additional Context (required)

| # | Field | Type | Why needed |
|---|---|---|---|
| 5 | **Sport selector** | dropdown (Football/Soccer, American Football, Cricket, Tennis, etc.) | All 3 books cover multiple sports; methods adapt |
| 6 | **Match context** | dropdown (League / Knockout / Final / Friendly) | Determines whether a draw is possible; affects default-rule logic |
| 7 | **Betting odds — Team A** | decimal (e.g., 1.85) | Chokoisky + Frawley: determines favorite vs underdog |
| 8 | **Betting odds — Team B** | decimal | Same |
| 9 | **Betting odds — Draw** | decimal (optional) | Only shown when match context permits a draw |
| 10 | **Team A founding chart** | date + time + place OR DB lookup | Rao: nations/clubs chart for Moon+Ascendant transposition |
| 11 | **Team B founding chart** | same | Same |

### 3.4 Captains & Jerseys — OPTIONAL Section (NEW per user request)

This section is **collapsed by default** and gated behind a checkbox:

> ☐ Include captains & jersey configuration
> *(Usually unavailable until minutes before kickoff. Optional in Rao's methodology.)*

When the checkbox is checked, the section expands to show:

| # | Field | Type | Notes |
|---|---|---|---|
| 12 | **Captain A jersey number** | integer | Rao: planetary-influence layer |
| 13 | **Captain B jersey number** | integer | Rao: planetary-influence layer |
| 14 | **Team A jersey color** | dropdown (Mars-red, Saturn-black/blue, Jupiter-gold, Venus-yellow, Mercury-green, Sun-maroon, Moon-white, Rahu-brown, Ketu-grey) | Rao: jersey-color layer |
| 15 | **Team B jersey color** | same dropdown | Rao: jersey-color layer |

When the section is collapsed/unchecked, the Rao engine runs **without the planetary-influence layer** and reports a slightly reduced confidence for Engine 1 (note this in the output: "Planetary influence layer skipped — captain/jersey data not provided"). The other two engines (Chokoisky, Frawley) are unaffected because they don't use this data.

**Use case the UI must support**: User adds a match on Friday for a Saturday game without captain info. Engine 1 runs in "Game Analysis + Nations' Charts" mode (no Planetary Influence). On Saturday morning, user opens the pending match record, checks the captain/jersey box, enters the data, and re-runs the analysis — Engine 1 then runs in full mode. The original (pre-captain-data) verdict is preserved in history; the new verdict is added as a revised version. Both versions feed the ML training set (with metadata distinguishing them).

### 3.5 For Historical Match Add — Scoreline (NEW per user request)

When the user is **adding a historical match** (i.e., a game that has already been played), an additional collapsible section appears:

| # | Field | Type |
|---|---|---|
| 16 | **Final score Team A** | integer (nullable) |
| 17 | **Final score Team B** | integer (nullable) |
| 18 | **Match status** | dropdown: Completed / Walkover / Abandoned / No result / D/L method applied |
| 19 | **Notes** | free text (e.g., "Red card 65' Team B", "Rain delay 30 min") |

When adding a historical match with scoreline, the app still runs the three engines for research purposes (you want to know what the engines WOULD have predicted, even though you already know the result). The verdict is stored but tagged as `post-hoc-analysis=true` so the ML pipeline knows this was a retrospective analysis (which may carry different statistical behavior than real-time predictions).

### 3.6 Auto-Conversions (Backend)

When the user submits the form:

1. **GMT → Local**: convert the GMT kickoff time to local time at the venue, using `tzfpy` to look up IANA timezone from lat/long, then `pytz` for the conversion. Handle DST correctly.
2. **Favorite determination**: lower decimal odds = favorite; the other team = underdog. If the two odds are within ±0.05 of each other, flag "no clear favorite" — this disables Frawley's event-chart method (see §7) and shows a warning.
3. **Draw possibility**: from sport + match context. Knockout finals and tennis cannot draw; league matches can.
4. **Sandhi guardrails** (see §10.2): if the kickoff falls in a sandhi window, show a non-blocking warning.

---

## 4. Chart Computation Backend

The Python FastAPI microservice exposes:

```
POST /chart
Body: { date, time_gmt, lat, long, ayanamsha: "lahiri"|"krishnamurti"|"tropical" }
Returns: {
  d1: { ascendant_deg, houses: [12 cusps with signs], planets: {Su, Mo, Ma, Me, Ve, Ju, Sa, Ra, Ke, Ur, Ne, Pl, Ce, Ch, Uk, Gu} },
  d9: { ascendant_deg, planets: same set },
  cusps_placidus: [12 deg/sign pairs],
  cusps_wholesign: [12 sign pairs],
  sublords: [12 cusp sublords],          # Krishnamurti
  antiscia: { per planet: deg+sign },
  speeds: { per planet: deg/day },       # detect stations
  combustions: [list of combust planets],
  planetary_wars: [list of planet pairs within 1°],
  nakshatra_of_moon, tithi, day_of_week
}
```

### Ayanamsha selection per engine

| Engine | Zodiac | Ayanamsha | House system |
|---|---|---|---|
| Rao | Sidereal | Lahiri | Whole Sign |
| Chokoisky | Sidereal | Lahiri (Krishnamurti for sublords only) | Placidus (with cuspal degrees) |
| Frawley | Tropical | None | Placidus (with cuspal degrees) |

The backend must compute the chart three times — once per engine's ayanamsha/house setting — so the three engines each see the chart the way their author intended.

### Required reference tables (load into DB)

1. Rao's planetary friendships (Friend / Neutral / Enemy for all 9 grahas — see Rao p.39)
2. Chokoisky's planet-on-cusp effects table (his table 4.1, p.63–64)
3. Chokoisky's D9 planet effects table (his table 5.3, p.95–96 — note Mars, Mercury, Venus have OPPOSITE effects in D9)
4. 108 Navamsha syllable table (Chokoisky table 7.1, p.142)
5. 28 Nakshatra yogatara positions and effects (Chokoisky table 8.1, p.160–161)
6. Planet dignity table (own sign / exaltation / debilitation / dig bala — Chokoisky table 3.1, p.46)
7. Planetary speed ranges for station detection (Chokoisky p.47)
8. Antiscia sign-pair table (Frawley Appendix 1, p.187)
9. Arabian Parts formulae (Frawley Appendix 2 — only Fortuna and Resignation used)
10. Common national team founding charts (England, Brazil, Germany, India, Australia, New Zealand, etc.)
11. Common club founding charts (Premier League, La Liga, IPL franchises)
12. **Wikipedia article name disambiguation table** (e.g., "Old Trafford" → "Old Trafford (football)"; "Camp Nou" → "Spotify Camp Nou") — first lookup uses this table, fallback uses Wikipedia search with disambiguation pages

---

## 5. Engine 1 — Dr. Ravi Rao's Inclusive Methodology

**Source**: *Sports Astrology* by Dr. Ravi Rao (2017), §3 "Inclusive Methodology of Sports Astrology" and the case studies in §2–4.

### 5.1 Chart Setup

- Ayanamsha: **Lahiri** (sidereal)
- House system: **Whole Sign**
- Match chart time: **kickoff time at venue** (Rao uses kick-off for football; toss time for cricket — for this app, always kickoff)
- **Ascendant allocation**: Rao allocates the ascendant to the toss winner for cricket. **For football, use the favorite team (lower odds) as the Native (Lagna)**, and the underdog as the Rival (7th house). If odds are equal, fall back to Team A as Native.
- The 7th house automatically becomes the Rival's ascendant.

### 5.2 House Significations (modified from Donald Bradley)

For the Native (favorite) team — read these houses from the Lagna:

| House | Signification |
|---|---|
| 1st | Ascendant — team strength, confidence |
| 2nd | Fans & Odds — fan sentiment, betting odds |
| 3rd | Coach & Captain — strategy, communication, courage |
| 5th | Game — on-field execution, momentum, vitality |
| 10th | Score — goals/runs scored (midheaven = status) |
| 12th | Penalties — extras given away (free kicks, cards, dropped catches) |

For the Rival (underdog) — read the same six significators from the 7th house:

| House (from Lagna) | Rival Signification |
|---|---|
| 7th | Rival Ascendant |
| 8th | Rival Fans & Odds |
| 9th | Rival Coach & Captain |
| 11th | Rival Game |
| 4th | Rival Score |
| 6th | Rival Penalties |

### 5.3 Analysis Steps

**Step 1 — Game Analysis (assign 0–3 points per parameter per team)**

Assess in this strict order (Rao emphasizes order matters):

**Primary parameters (judge first):**

1. **Ascendant** — is it aspected? by what? Same for ascendant lord placement and aspects.
2. **Ascendant lord** — placement, conjunctions, aspects. (e.g., "debilitated Mercury conjunct Sun under Jupiter's 9th aspect")
3. **Score house** (10th for Native, 4th for Rival) — planets in it, aspects to it, house-lord condition.

**Secondary parameters (then assess):**

4. **Game + Coach & Captain together** (5th + 3rd for Native; 11th + 9th for Rival) — analyze as a pair because Game executes the Captain's strategy.
5. **Fans & Odds** (2nd for Native; 8th for Rival) — 8th house being house of defeat impacts rival fans heavily.
6. **Penalties** (12th for Native; 6th for Rival) — free runs given to the opposition.

**Points system (per Rao p.41):**

| Condition | Points |
|---|---|
| Malefic aspect / enemy relation | 0 |
| Neutral (no planet, no aspect) | 1 |
| Benefic aspect / friend relation | 2 |
| Powerful benefic (exalted, own sign, strong conjunction) | 3 |

**Step 2 — Nations' Charts Analysis**

For each team, look up the founding chart of the team's nation (international matches) or club/franchise (domestic leagues) — the user supplied this in inputs 10 and 11.

1. Extract the nation's **Moon sign** and **Ascendant sign**.
2. **Transpose nation Moon onto the match chart**: find which house of the match chart the nation Moon occupies. Note aspects/conjunctions to transit planets.
3. **Transpose nation Ascendant onto the match chart**: same procedure.
4. Check the influence of larger planets (Saturn, Jupiter, Mars) on the nation's Moon and Ascendant in the transit chart. This is **especially important in case of a tie** in the Game Analysis.
5. Assign points using the same 0–3 scale.

**Critical exception (Rao p.30):** If a match is interrupted (rain, D/L method, crowd trouble, power failure), the methodology must be **set aside**. The nation's chart showing Saturn aspecting the 8th house is a strong interruption indicator. Surface a warning when this is detected.

**Step 3 — Planetary Influence (OPTIONAL — skipped when captain/jersey toggle is unchecked)**

**3a. Captain's Jersey Number**

1. Reduce jersey number to single digit (e.g., 42 → 4+2 = 6; 99 → 9+9=18 → 9).
2. Map to ruling planet:
   - 1 = Sun, 2 = Moon, 3 = Jupiter, 4 = Rahu, 5 = Mercury, 6 = Venus, 7 = Ketu, 8 = Saturn, 9 = Mars
3. Reduce the **match date** (day of month) to a single digit, find its ruling planet.
4. Determine relationship (Friend / Neutral / Enemy) using Rao's friendship table (p.39).
5. For outdoor sports, Mars and Jupiter are key significators. For football specifically, **Mars is the influencing planet** (the game is played with the legs).

**3b. Day of Week**

- Sunday=Sun, Monday=Moon, Tuesday=Mars, Wednesday=Mercury, Thursday=Jupiter, Friday=Venus, Saturday=Saturn
- Check the relationship between the day-lord and the captain's jersey-number planet.
- Favorable jersey numbers for captains (per Rao p.38): **9 and 7 are best**, then 3, 5, 1. Unfavorable: 8, 4, 2.

**3c. Jersey Color**

Map team jersey color to planet using the same table:

| Planet | Number | Color | Day |
|---|---|---|---|
| Sun | 1 | Maroon | Sunday |
| Moon | 2 | White | Monday |
| Mars | 9 | Red | Tuesday |
| Mercury | 5 | Green | Wednesday |
| Jupiter | 3 | Gold | Thursday |
| Venus | 6 | Yellow | Friday |
| Saturn | 8 | Black, Blue | Saturday |
| Rahu | 4 | Brown | — |
| Ketu | 7 | Grey | — |

Check the relationship between the jersey-color planet and the day-of-week lord.

### 5.4 Engine 1 Output

- **Per-parameter points table**: 9 parameters × 2 teams (Ascendant, Asc lord, Score, Game+Coach, Fans & Odds, Penalties, Nation Moon, Nation Ascendant, Planetary Influence — last one marked "skipped" if toggle off)
- **Total score** per team
- **Verdict**: higher total wins
- **Goal differential**: not strictly quantified by Rao, but a wider margin (8+ points) suggests a more decisive victory; a 1–3 point margin suggests a close match
- **Caveats**: any Saturn-in-8th warnings, any interruption-risk flags, any debilitation warnings, any "planetary-influence-skipped" notice
- **Format**: detailed house-by-house reasoning in markdown, then the verdict table
- **ML features emitted** (see §12): per-parameter point differentials, total point differential, planetary-influence-included flag, Saturn-in-8th flag

---

## 6. Engine 2 — Simon Chokoisky's Gambler's Dharma Method

**Source**: *Gambler's Dharma* by Simon Chokoisky (2017), chapters 3–8 plus appendices.

### 6.1 Chart Setup

- Ayanamsha: **Lahiri** for all chart work, **Krishnamurti** for sublord calculations only
- House system: **Placidus** (with cuspal degrees — critical)
- **Favorite = Lagna (1st house)**, Underdog = 7th house (the descendant)
- Compute **D1 (Rashi)** and **D9 (Navamsha)** charts, both with degree-level cusps
- Include **outer planets** (Uranus, Neptune, Pluto, Ceres, Chiron)
- Include **Upaketu** and **Gulika** upagrahas
- Include Moon's Nodes (Rahu, Ketu)

### 6.2 Multi-Tier Point System

Each technique awards points to either favorite (+) or underdog (−). Sum across all tiers for a final signed total.

| Tier | Technique | Points per instance |
|---|---|---|
| 1 | Victory houses | 2–4 per planet |
| 1 | Navamsha combinations | 5 per combo |
| 2 | SKY / PKY | 7–9 |
| 2 | Cuspal strength (D1) | 7–9 per planet (visible), 7 per invisible |
| 2 | Sublord strength | per scoring rules in §6.8 |
| 2 | Nakshatra tara | ~7 |
| 3 | Navamsha cuspal strength | 14–18 per planet (visible), 12–15 per invisible |

**Final interpretation**:
- Total > 0 → favorite wins
- Total < 0 → underdog wins
- Total between −3 and +3 → likely draw (if draw is possible)
- **Goal differential** = `|Total| / 3`, rounded to nearest integer (for soccer). For other sports, calibrate divisor.

### 6.3 Technique 1 — Victory Houses (Tier 1)

- Favorite victory houses: **1, 3, 6, 10, 11**
- Underdog victory houses (from 7th): **7, 9, 12, 4, 5**

Count malefics (Saturn, Mars, Sun, Rahu, Ketu) in each team's victory houses. **Benefics count only if "exaggerated"**: exalted, retrograde, own nakshatra, own sign, dig bala, or full Moon.

Points:
- 2.5 per standard malefic
- 3 per extra-strong malefic (exalted, dig bala, own sign)
- 2 per debilitated malefic
- 2.5 per exaggerated benefic
- 2 per debilitated benefic

Apply sign: positive points → favorite, negative points → underdog.

### 6.4 Technique 2 — SKY / PKY (Tier 2)

- **SKY (Shubha Kartari Yoga)**: benefics (Jupiter, Venus, Mercury, Moon) in both 12th and 2nd from the 1st house OR from the 7th house. SKY around the favorite's lagna = strong + for favorite. SKY around underdog's 7th cusp = strong + for underdog.
- **PKY (Papa Kartari Yoga)**: malefics (Saturn, Mars, Sun, Rahu, Ketu) in 12th and 2nd from a cusp. PKY = negative for that team.
- **Note**: A single Rahu or Ketu on one side alone does NOT form a full SKY/PKY — it produces half-effect only (one half of the game). Full PKY/SKY requires two planets.
- SKY is more powerful than PKY (Chokoisky p.42).
- 7–9 points for a full SKY, 3–4 for a marred SKY (one side is Sun or Ketu).

### 6.5 Technique 3 — Cuspal Strength in D1 (Tier 2)

Active cusps (ignore 3/9 and 5/11 unless "stolen"):
- 1/7 axis (team itself)
- 4/10 axis (glory / victory)
- 6/12 axis (fighting spirit)

Orbs:
- Visible planets: 2°30′
- Invisible (Rahu, Ketu, Uranus, Neptune, Pluto, Ceres, Chiron, Upaketu, Gulika): 2°
- Exalted or retrograde planets: extend orb ~30′

Planet effects (Chokoisky's table 4.1):

| Planet | On 1/7 cusp | On 4/10 cusp | On 6/12 cusp |
|---|---|---|---|
| Sun | − | − | − |
| Moon | − | − | − |
| Mars | + | − | + |
| Rahu | + | + | + |
| Jupiter | + | + | + |
| Saturn | − | + | + |
| Mercury | ± (depends on ruled houses) | ± | + |
| Ketu | − | − | − |
| Venus | + | + | + |
| Uranus | + if direct, − if Rx | same | same |
| Neptune | − if direct, + if Rx | same | same |
| Pluto | − | + | − |
| Upaketu | − | − | − |
| Gulika | − | + | ± (research) |

**Stolen cusps**: if a power cusp falls in a different whole-sign house, adjust:
- Power-to-neutral: reduces effect
- Neutral-to-power: activates otherwise-dormant cusp
- Power-to-power: shifts effect between teams (only 6/7 and 12/1 swaps possible)

### 6.6 Technique 4 — Navamsha Cuspal Strength (Tier 3 — MOST POWERFUL)

Compute the D9 chart with **exact degrees** (use the 6.67 divisor — see Chokoisky p.91):

1. Find D9 Lagna degree and D9 7th cusp degree (same degree, opposite sign).
2. Check which planets fall within 2°30′ (visible) or 2° (invisible) of the D9 1st or 7th cusp.
3. Each such planet exerts a **third-tier** effect on its team.

**Planet effects in D9** (note OPPOSITE effects for Mars, Mercury, Venus):

| Planet | Effect on 1/7 D9 cusp | Notes |
|---|---|---|
| Sun | − | Cautious, low-scoring |
| Moon | − | Lazy, unstable |
| **Mars** | **−** | Frustration, anger, self-undoing (OPPOSITE of D1!) |
| Rahu | + | Ambition |
| Jupiter | + | Luck, optimism |
| Saturn | − | Depression, slowness |
| **Mercury** | **+** | Skill, speed (OPPOSITE of D1!) |
| Ketu | − | Confusion |
| **Venus** | **−** | Complacency, prima donna (OPPOSITE of D1!) |
| Uranus | + if direct, − if Rx | Electric |
| Neptune | − if direct, + if Rx | Inspiration when Rx |
| Pluto | − | Heaviness |
| Upaketu | − | Like Ketu |
| Gulika | − | Defeat |

A planet tightly conjunct (<1°) a D9 cusp transfers its bodily D1 placement to the D9 — "double whammy" (Chokoisky p.110).

### 6.7 Technique 5 — Nama Pada (Tier 3)

Determine the **10th cusp (MC) degree in D1**. Find which navamsha that degree falls in, then look up the Sanskrit syllable in the 108-syllable table (Chokoisky table 7.1, p.142).

If the syllable matches the first syllable of either team's name (city or nickname):
- Match = **third-tier boost** for that team (14–18 points)

**Diphthong rule**: 'eh' also = 'ai', 'oh' also = 'au' (so 't.e' matches "Tigers" via the eh→ai diphthong)

**Substitutions**: v for w, pha/pa for f, jha for z (Sanskrit lacks these sounds).

### 6.8 Technique 6 — Sublords (Tier 2)

Use **Krishnamurti ayanamsha** for this technique alone.

1. Find sublord of 1st cusp and sublord of 7th cusp.
2. For each sublord, determine its house significators using the KP method:
   - Column A: sign lord of the cusp (1 pt)
   - Column B: planets in the nakshatra of the cusp's sign lord (2 pts)
   - Column C: planets occupying that house (Placidus) (3 pts)
   - Column D: planets in the nakshatra of the house occupants (4 pts)
3. For each sublord, sum the points of all houses it signifies with these signs:
   - Houses 1, 3, 6, 10, 11 → **+** (victory houses)
   - Houses 4, 5, 7, 8, 9, 12 → **−**
   - House 2 → +0.5
   - House 8 → −1
4. Compute point difference between sublord 1 and sublord 7. Big difference = clear winner; difference ≤3 = draw.

**Sublord Array** (Tier 1, 7–9 pts): if ALL 12 sublords fall in victory houses for the same team, give a tier-1 boost.

### 6.9 Technique 7 — Nakshatra Taras (Tier 2)

Check whether the lords of houses 1, 7, 4, 10 (for either team) or the cusps of houses 1, 7, 4, 10 fall within **1° of a major yogatara** (fixed star).

Key stars (use these primarily):

| Star | Position | Effect on cusp/lord |
|---|---|---|
| **Regulus** (Magha) | 6° Leo | Strong victory (kingly) |
| **Pollux** (Punarvasu) | 29°30′ Gemini | Strong victory (full quiver) |
| **Vega** (Abhijit) | 21°30′ Sag | Victory ("the victorious") |
| **Spica** (Chitra) | 29°55′ Virgo | LOSS when on a cusp |
| **Antares** (Jyeshtha) | 16° Scorpio | Largely nullified by Aldebaran opposite |
| **Algol** | 26° Taurus | Moderate negative (beheading/loss) |
| **Wasat** | 25° Gemini | Behaves like Saturn |
| **Hyades** | 11–13° Taurus | Mild positive |

If both teams' significators are on the same star, the one closer to the star wins.

### 6.10 Technique 8 — Planetary War (Graha Yuddha)

If two planets are within 1° of each other, they are at war. Only consider wars involving lords of houses 1, 10 (favorite) or 7, 4 (underdog). The winner = the brighter planet (lesser magnitude; Venus almost always wins). Losing planet is destabilized.

### 6.11 Engine 2 Output

- Breakdown table: one row per technique with points awarded
- Cumulative signed total
- Predicted winner (favorite if total > 0, underdog if < 0, draw if |total| ≤ 3)
- Predicted goal differential: `|total| / 3` rounded
- Confidence: high if total > 9 or < −9; medium if 5–9; low if < 5
- Notes on any especially decisive testimonies (D9 cusp planets, SKY, sublord dominance)
- **ML features emitted**: per-technique signed points, total, D9-cusp-planet flag, sublord-diff, nama-pada-match flag

---

## 7. Engine 3 — John Frawley's Event Chart Method

**Source**: *Sports Astrology* by John Frawley (Apprentice Books, 2007), Chapter 2 "The Chart for the Event".

### 7.1 Chart Setup

- Zodiac: **Tropical** (Frawley is a traditional Western astrologer — NOT Vedic)
- House system: **Placidus** (strictly — Regiomontanus is for his horary method, which we are NOT using)
- Match chart cast for **kickoff time at venue** (must be precise to the minute if possible)
- **Favorite = Lord 1 (1st house ruler) + Lord 10 (10th house ruler = favorite's success)**
- **Underdog = Lord 7 (7th house ruler) + Lord 4 (4th house ruler = underdog's success)**
- The other houses are neutral and ignored

### 7.2 Analysis Steps (in order of priority)

**Step 1 — House Placement of Significators (most decisive)**

For Lords 1, 4, 7, 10, check proximity to cusps of houses 1, 4, 7, 10:

- **"On the cusp"**: within 2–3° before the cusp AND in the same sign as the cusp → planet **controls** that house
- **"Just inside"**: within 2–3° after the cusp AND in the same sign as the cusp → planet is **controlled by** that house

Key testimonies (apply to favorite unless stated):

| Placement | Verdict |
|---|---|
| Lord 1 on 7th cusp | Favorite WINS (strong) |
| Lord 1 just inside 7th house | Favorite LOSES (strong) |
| Lord 7 on 1st cusp | Underdog WINS |
| Lord 7 just inside 1st house | Underdog LOSES (favorite wins) |
| Lord 10 on 7th cusp | Favorite WINS |
| Lord 10 just inside 7th house | Underdog WINS |
| Lord 7 on 10th cusp | Underdog WINS |
| Lord 7 just inside 10th house | Favorite WINS |
| Lord 1 on 1st cusp or just inside 1st | Favorite WINS (weaker — own castle) |
| Lord 4 on 4th cusp or just inside 4th | Underdog WINS (weaker) |
| Lord 10 on 10th cusp or just inside 10th | Favorite WINS (weaker) |

**Retrograde planet on enemy cusp**: still positive but weaker (like an army going home from a siege).

**Retrograde planet inside enemy house**: no benefit (still in prison even if rattling the door).

**Step 2 — Antiscia of Significators (CRITICAL — often decisive)**

Calculate antiscion for Lords 1, 4, 7, 10. Antiscion = reflection around 0° Cancer/Capricorn. Sign-pair table:

```
Aries ↔ Virgo
Taurus ↔ Leo
Gemini ↔ Cancer
Libra ↔ Pisces
Scorpio ↔ Sagittarius
Capricorn ↔ Aquarius
```

Degree rule: `original_degree + antiscion_degree = 30°` (use 29°60′ trick for arithmetic).

If the antiscion of a significator sits on or just inside an enemy house cusp (within same 2–3° rule), apply the same testimony as the bodily placement.

**Step 3 — Moon Placement**

The Moon is not assigned to either team. It shows the "flow of events":
- Moon applying to or close inside 1st or 10th cusp → favorite wins
- Moon applying to or close inside 7th or 4th cusp → underdog wins
- Check Moon's antiscion too

**Step 4 — Part of Fortune (Antiscion only — NOT bodily placement)**

Compute Part of Fortune = Asc + Moon − Sun (do NOT reverse at night). Use the antiscion of Fortuna only — the bodily placement is ignored for house judgement.

- Antiscion of Fortuna close to 1st cusp → favorite wins
- Antiscion of Fortuna close to 7th cusp → underdog loses (favorite wins)
- Antiscion of Fortuna close to 10th cusp → favorite wins
- Antiscion of Fortuna close to 4th cusp → underdog wins

**This is one of the most powerful single testimonies in event charts.**

Check also: Fortuna combust (within 2° of Sun) → harms favorite.

**Step 5 — Moon's Aspects (often decisive)**

Range limit:
- Football (soccer, 90 min) → max 5° of Moon travel
- Add 1° if extra time is possible
- Other sports: see Frawley p.86

Rules:
- Only APPLYING aspects count (separating = past, ignore)
- The end of the Moon's current sign is the hard limit (do NOT cross into next sign)
- Exception: first-class cricket may cross ONE sign boundary

**Whichever of Lords 1, 7, 4, 10 is the Moon's LAST aspect within range → that team wins.**

Special rules:
- Bodily conjunctions are usually FINAL (don't take the Moon past them)
- Short-range antiscial conjunctions (within 5–6°) are NOT final
- Long-range antiscial conjunctions (>10°, cricket only) ARE final

**Step 6 — Aspects to Fortuna**

- Moon conjunct/trine/sextile Fortuna or its antiscion → favorite wins
- Moon square/oppose Fortuna or its antiscion → underdog wins
- Lord 1 conjunct Fortuna or its antiscion → favorite wins
- Lord 1 oppose Fortuna or its antiscion → underdog wins
- Lord 7 conjunct Fortuna or its antiscion → underdog wins
- **Anomaly**: Lord 7 bodily opposition to Fortuna → underdog wins
- Lord 7 oppose antiscion of Fortuna → favorite wins

**Aspects to Fortuna are FINAL** — ignore all subsequent Moon aspects.

**Step 7 — Dispositor of Fortuna**

- Dispositor of Fortuna applying to conjunct Fortuna → favorite wins
- Dispositor of Fortuna applying to oppose Fortuna → underdog wins
- If dispositor is also Lord 10 or 4: prioritize Fortuna role
- If dispositor is also Lord 1, 7, or the Moon: ignore Fortuna role

**Step 8 — Miscellaneous Testimonies**

- **North Node on significator** → +
- **South Node on significator** → −
- **Combustion** (within 2° of Sun) → destructive
- **Cazimi** (within 17′ of Sun) → no effect in event charts (no king in this context)
- **Pluto** → destructive to favorite when:
  - On 1st cusp (or applying to it)
  - Conjunct or opposing Fortuna or its antiscion
  - On the 2nd cusp (minor negative for favorite)
  - Pluto favors underdogs more than favorites in general
- **Saturn** (when not Lord 1 or 7) → malefic, afflicts whatever it touches
- **Uranus** → applying to MC strongly favors favorite; conjunct Fortuna → favorite wins; opposing Fortuna → underdog wins
- **Neptune** → inconsistent, usually ignore
- **Retrogradation** → no independent effect, but affects which aspects perfect

**Step 9 — Default Rule**

If NO testimony at all → **favorite wins** (they are favored for a reason). Strong house placements (especially of Lord 1 or 7) usually outweigh all other testimonies.

### 7.3 Engine 3 Output

- Testimony list, each with strength rating (weak / medium / strong)
- Net verdict (favorite wins / underdog wins / draw)
- Goal prediction for low-scoring sports (soccer):
  - Count testimonies for winning team
  - More testimonies → more goals
  - Typical soccer: 1–3 goals for winner, 0–1 for loser
  - Do not predict a margin > 4 goals — statistically rare
- Draw indicator: testimonies roughly balanced
- Late-winning-goal indicator: Moon's final aspect completing late in its range
- **ML features emitted**: testimony count, strongest-testimony type, verdict, late-goal flag, pluto-on-cusp flag

---

## 8. Overall Outlook Synthesis

### 8.1 Comparative Table

Display a table comparing all three engines:

| Methodology | Predicted Winner | Predicted Score / Goal Diff | Confidence | Key Testimonies | Caveats |
|---|---|---|---|---|---|
| Rao — Inclusive Methodology | Team X | 2–1 (close) | Medium | Jupiter exalted in 2nd; Mars aspect on rival asc | Saturn in 8th of nation chart — interruption risk |
| Chokoisky — Gambler's Dharma | Team X | +2 goals | High | D9 Jupiter on 7th cusp (+18); Sublord diff +9 | None |
| Frawley — Event Chart | Team X | 2–1 | High | Lord 1 on 7th cusp (strong); Moon → Lord 10 | None |

### 8.2 Synthesis Output

The synthesis is **ML-weighted**: each engine's verdict is multiplied by a learned weight (see §12 for how weights are learned). Initially (cold start) all three engines have equal weight = 1.0.

1. **Consensus winner**:
   - All 3 agree → "Very strong consensus: Team X"
   - 2 of 3 agree → "Strong consensus: Team X (one dissent: Engine Y)"
   - 1 each → "No consensus — high uncertainty; lean toward Frawley's verdict by default"

2. **Disagreement analysis**: When engines disagree, explain which is most reliable for this match context:
   - If match has clear favorite → Frawley's event-chart is most decisive
   - If D9 cuspal planets are present → Chokoisky's verdict is highly reliable
   - If match could be interrupted → Rao's verdict is unreliable; weight Chokoisky + Frawley more
   - **ML override**: if the ML model has discovered that, say, "Rao agrees with Chokoisky" is a combination that has historically achieved 85% accuracy (significantly higher than either alone), surface this finding prominently: "Historical pattern alert: When Rao and Chokoisky agree, accuracy is 85% over N matches — strong signal."

3. **Combined goal range**: take the **intersection** of all engines' predicted ranges. Display as "Most likely: 2–1. Plausible range: 2–0 to 3–1."

4. **Confidence score** (0–100%): based on:
   - Number of engines agreeing (3 = +40, 2 = +25, 1 = +10)
   - Magnitude of each engine's point differential (Rao: >8 points = strong; Chokoisky: >9 = strong; Frawley: 2+ strong testimonies = strong)
   - Quality of testimonies (D9 cusp planets = high; SKY = high; Lord on cusp = high)
   - Sandhi/interruption risks = −15 each
   - **ML confidence multiplier**: if the discovered combination weights for this verdict pattern sum to >2.0 (out of 3.0 max), boost confidence by +15; if <1.0, reduce by −10

5. **Other observations** the engines collectively surface:
   - Likely drawn match (if draw possible and all engines show narrow margin)
   - Likely low-scoring vs high-scoring
   - Late winning goal (Frawley's Moon completing late in range)
   - Saturn-in-8th caveat (potential interruption)
   - D/L method risk (weather)
   - Star captain impact (Rao jersey-number significance)
   - Jersey color clash insights
   - Star player significance (if nama pada matches team name)
   - Planetary war winner indication

---

## 9. UI/UX Requirements

### 9.1 Page 1 — Analyze (Match Setup Form + Live Analysis)

- Multi-section form (collapsible sections for Core / Captains & Jerseys (optional toggle) / Odds / Founding Charts / Scoreline (historical add only))
- Smart defaults: pre-fill team data from DB if team is recognized
- **Wikipedia stadium lookup** with manual override per §3.2
- **Live GMT → local conversion preview** as the user enters time and venue
- **Optional captain/jersey section** with explicit checkbox per §3.4
- Validation:
  - Sandhi warnings (eclipse ±3 days, solar sankranti, sunrise/sunset ±30 min)
  - Equal-odds warning (disables Frawley engine with explanation)
  - Missing-team-founding-chart warning (Rao needs this)
- On submit: compute charts, run three engines in parallel, show results dashboard
- Two submit buttons: **"Analyze & save as pending"** (for upcoming matches) and **"Analyze as historical (with scoreline)"** (for past matches, requires scoreline fields filled)

### 9.2 Page 2 — Analysis Dashboard (results view)

Layout: top section = Overall Outlook (sticky), then three engine cards below.

**Overall Outlook section** (always visible):
- Comparative table (per §8.1)
- Consensus winner with confidence %
- Combined goal range
- **ML insight banner**: if the ML model has discovered a high-accuracy combination matching this match's verdict pattern, surface it here (e.g., "📊 Historical pattern: When D9 Jupiter is on the favorite's cusp AND Rao's nation-Moon is in the 10th, the favorite has won 18 of 22 matches (82%). This match matches that pattern.")
- Cautions box (anti-betting notice + any engine-specific caveats)

**Engine cards** (one per book, expandable):
- Header: book title + author + methodology summary
- Chart visualization (D1 for Rao/Frawley; D1 + D9 side-by-side for Chokoisky)
- Per-parameter breakdown table
- Points tally / testimony list
- Verdict
- Quote from the source book explaining the methodology
- **Save-to-dataset button** (top right of each card): saves the full analysis snapshot to the historical dataset

### 9.3 Page 3 — Historical Dataset (NEW per user request — major page)

A full CRUD table for browsing, searching, filtering, and managing all match records.

**Columns**: Date / Team A / Team B / Scoreline (or "Pending") / Status / Sport / Venue / Predicted Winner / Actual Winner / Correct? / Engines agreed? / ML pattern / Notes / Actions

**Filters**:
- Date range
- Sport
- Status (Pending / Completed / Abandoned / Walkover)
- Engine agreement (all 3 agree / 2 of 3 / all disagree)
- Prediction correctness (correct / incorrect / pending)
- ML pattern present (yes / no)
- Has captain data (yes / no)

**Actions per row**:
- **View** → opens the full analysis view (same as Page 2 but read-only)
- **Edit** → opens the edit form (allows editing scoreline, status, notes, and any input fields; re-runs engines on save if input fields changed)
- **Mark result** → quick-action modal to enter scoreline for a pending match without opening the full edit form
- **Re-analyze** → re-runs the three engines with the existing inputs (useful after a reference-table update)
- **Delete** → soft-delete (preserves the record for audit but hides from default view; only available to admin role)

**Add buttons** (top of page):
- **Add historical match** → opens the form with the Scoreline section expanded and required
- **Add new match for analysis** → opens the form with the Scoreline section hidden (saved as `pending` status)

**Export**:
- CSV export of filtered records (for offline analysis)
- JSON export of full records (with chart snapshots) for backup

### 9.4 Page 4 — Match Record Detail & Edit (NEW per user request)

For each match record (whether newly analyzed or historically added):

- All input fields (editable)
- Scoreline section:
  - For pending matches: shows "Pending — add scoreline" prompt with a quick-add form
  - For completed matches: shows scoreline, status, notes (all editable)
- Chart snapshots (the D1 and D9 charts as captured at analysis time — NOT recomputed on view, only on re-analyze)
- All three engine verdicts (snapshotted at analysis time)
- **Edit timeline**: shows every edit made to the record with timestamp and user (for audit)
- **Re-run analysis button**: re-runs engines with current input fields; the new verdict is added as a version, the old verdicts are preserved for comparison

### 9.5 Page 5 — ML Training Dashboard (NEW per user request)

Shows the machine-learning model's current state and history.

**Top metrics**:
- Total matches in dataset (broken down by status)
- Current model accuracy (overall + per engine + per combination)
- Most recent training run timestamp
- Cold-start indicator (if <30 completed matches, show "Insufficient data — using equal weights")

**Combination weights table** (top section):
- Lists every astrological combination the model has discovered with non-trivial predictive power
- Columns: Combination description / Sample size / Historical accuracy / Current weight / Trend (↑ ↓ →)
- Example rows:
  - "Rao + Chokoisky agree on winner, Frawley disagrees" — N=45, acc=78%, weight=1.4
  - "D9 Jupiter on favorite's cusp" — N=22, acc=82%, weight=1.6
  - "Lord 1 on 7th cusp (Frawley strong testimony)" — N=38, acc=84%, weight=1.7
  - "Rao Saturn-in-8th + Frawley Pluto on 1st" — N=12, acc=92% (upset indicator), weight=2.1
- Sortable by accuracy, sample size, or weight
- Each row expands to show the matches that contributed to the pattern

**Training controls**:
- "Retrain now" button (triggers a fresh training run)
- "Schedule nightly retrain" toggle (default ON)
- "Rollback to previous model" dropdown (shows last 10 model versions with their accuracy)

**Per-engine accuracy chart**:
- Bar chart showing accuracy of each individual engine over time (last 30, 60, 90 days)
- Bar chart showing accuracy of common combinations over time

**Cold-start handling**:
- Until 30 completed matches exist, all engines have equal weight (1.0) and combinations are not yet computed
- Show "Dataset has N matches. Need 30 to start ML training. Currently in equal-weight mode."

### 9.6 Page 6 — Settings

- Manage reference data tables (team founding charts, venue coordinates with re-verify-from-Wikipedia button, sport presets, ayanamsha defaults)
- Toggle which engines/techniques are active
- User account settings (if auth is enabled)
- ML configuration: minimum sample size for combination, minimum accuracy threshold, max combination length (default 3 features)

### 9.7 Page 7 — Detailed Chart View (drill-down)

- Interactive chart wheel (D1)
- Navamsha chart (D9)
- House table with cusps (Placidus + Whole Sign side-by-side)
- Planet positions table (longitude, speed, dignity, combustion status)
- Antiscia table
- Sublord table (Krishnamurti)

### 9.8 Visual Design

- Clean, scholarly aesthetic — think Bloomberg terminal meets academic journal
- Each engine gets a distinct accent color (Rao = saffron, Chokoisky = indigo, Frawley = forest green)
- ML features use a neutral teal
- Use serif typography for body text (readability for long-form analysis)
- Loading states: each engine's analysis runs in parallel; show progress per engine

---

## 10. Cautions & Guardrails

### 10.1 Anti-Betting Notice (MANDATORY, PERSISTENT)

A banner must appear at the top of every page and cannot be dismissed:

> ⚠️ **For astrological research and educational purposes only.**
>
> Dr. Ravi Rao's foundational text *Sports Astrology* explicitly states: "I would go so far as to say that the method will not work for persons involved in betting. I would like to call it astrology's curse." This application does not facilitate gambling and must not be used for that purpose. Predictions are probabilistic estimates based on classical texts, not guarantees. The traditional 70/30 doctrine holds that astrologers are at best 70% accurate. Use these analyses as explorations of astrological method, not as betting advice.

### 10.2 Sandhi Guardrails

Display a non-blocking warning (do not block analysis) if the kickoff falls in any of these windows:

- Eclipse ±3 days
- Solar sankranti (Sun at 29°+ of any sign — Sun entering a new sign)
- Sunrise or sunset at the venue ±30 minutes
- Any major planet (Jupiter, Saturn, Mars, Venus, Mercury) stationary within ±24 hours
- Moon void of course (last aspect in sign already separating) — note for Frawley's event-chart method this is NOT a block, just a flag

### 10.3 Equal-Odds Block

If Team A and Team B odds are within ±0.05 of each other, Frawley's engine cannot be applied (the method requires a clear favorite). Show a notice in the Frawley card: "Frawley's event-chart method requires a clear favorite. With equal odds, this engine is disabled. Rao and Chokoisky engines still run."

### 10.4 Interruption Caveat (Rao)

If Rao's nation-chart analysis detects Saturn aspecting the 8th house of either nation's chart in the transit, show: "Rao's methodology cautions that this configuration indicates potential match interruption (weather, crowd, technical). If an interruption occurs and the D/L method (or equivalent) is invoked, this prediction must be set aside per Rao's explicit exception."

### 10.5 Post-Hoc Analysis Caveat

For historical matches added with the scoreline already known, mark the verdict cards with: "Post-hoc analysis: the user already knew the result when this analysis was generated. The verdict may be biased by the user's choice of inputs. Use with caution in ML training — flag this in the dataset as `post_hoc=true`."

---

## 11. Critical Implementation Notes

### 11.1 Database Schema (Prisma)

```prisma
model Team {
  id              String   @id @default(cuid())
  name            String
  displayName     String
  nationOrClub    String   // "nation" | "club" | "franchise"
  foundingDate    DateTime?
  foundingTime    String?  // HH:MM in founding-place local time
  foundingPlace   String?
  foundingLat     Float?
  foundingLong    Float?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  matchesAsA      Match[]  @relation("MatchTeamA")
  matchesAsB      Match[]  @relation("MatchTeamB")
}

model Venue {
  id              String   @id @default(cuid())
  name            String   @unique
  canonicalName   String?
  lat             Float
  long            Float
  coordinateSource String  // "wikipedia" | "openstreetmap" | "manual"
  lastVerifiedAt  DateTime?
  wikipediaPageId Int?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  matches         Match[]
}

model Match {
  id              String   @id @default(cuid())
  sport           String   // "football" | "american_football" | "cricket" | etc.
  context         String   // "league" | "knockout" | "final" | "friendly"
  kickoffGMT      DateTime
  kickoffLocal    DateTime
  teamAId         String
  teamA           Team     @relation("MatchTeamA", fields: [teamAId], references: [id])
  teamBId         String
  teamB           Team     @relation("MatchTeamB", fields: [teamBId], references: [id])
  venueId         String
  venue           Venue    @relation(fields: [venueId], references: [id])
  oddsA           Float
  oddsB           Float
  oddsDraw        Float?
  
  // Captain & jersey data (nullable — optional section)
  captainAJersey  Int?
  captainBJersey  Int?
  teamAJerseyColor String?  // Mars-red, Saturn-black, etc.
  teamBJerseyColor String?
  
  // Scoreline (null for pending matches)
  scoreA          Int?
  scoreB          Int?
  status          String   @default("pending")  // "pending" | "completed" | "abandoned" | "walkover" | "dl_method"
  notes           String?
  
  // ML metadata
  postHocAnalysis Boolean @default(false)
  hasCaptainData  Boolean @default(false)
  
  // Chart snapshots (JSONB for full chart data)
  chartD1Rao      Json?    // sidereal/whole-sign
  chartD1Chokoisky Json?   // sidereal/placidus
  chartD9Chokoisky Json?
  chartD1Frawley  Json?    // tropical/placidus
  
  // Engine verdicts (snapshotted)
  verdictRao      Json?    // { winner: "A"|"B"|"draw", scoreA, scoreB, pointsA, pointsB, features }
  verdictChokoisky Json?
  verdictFrawley  Json?
  
  // ML features
  mlFeatures      Json?    // extracted feature vector
  mlPatternMatches Json?   // list of combination IDs that matched
  mlConfidenceMultiplier Float?
  
  // Audit
  analysisVersions Json?  // array of { timestamp, verdicts } for re-analyses
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  @@index([kickoffGMT])
  @@index([status])
  @@index([teamAId, teamBId])
}

model MLCombination {
  id              String   @id @default(cuid())
  description      String   // human-readable description
  featureKeys     String[] // e.g., ["engine_agreement:rao_chokoisky", "d9_jupiter_on_favorite_cusp"]
  featureValues   Json     // the actual feature values that define this combination
  sampleSize      Int
  correctCount    Int
  accuracy        Float    // correctCount / sampleSize
  weight          Float   // applied multiplier in synthesis (default 1.0)
  engineScope     String? // null=all engines, or "rao"|"chokoisky"|"frawley"
  discoveredAt    DateTime @default(now())
  lastTrainedAt   DateTime @updatedAt
  active          Boolean @default(true)
  matches         MLCombinationMatch[]
}

model MLCombinationMatch {
  id              String   @id @default(cuid())
  combinationId   String
  combination     MLCombination @relation(fields: [combinationId], references: [id])
  matchId         String
  match           Match   @relation(fields: [matchId], references: [id])
  predicted       String  // "A" | "B" | "draw"
  actual          String
  correct         Boolean
  @@unique([combinationId, matchId])
}

model MLModelVersion {
  id              String   @id @default(cuid())
  versionNumber   Int
  trainedAt       DateTime @default(now())
  overallAccuracy Float
  engineAccuracies Json   // { rao: 0.65, chokoisky: 0.72, frawley: 0.70 }
  combinationCount Int
  sampleSize      Int
  isCurrent       Boolean @default(false)
  modelArtifactPath String? // path to joblib file
}

model EditAudit {
  id              String   @id @default(cuid())
  matchId         String
  fieldName       String
  oldValue        String?
  newValue        String?
  editedAt        DateTime @default(now())
  editedBy        String?
  match           Match   @relation(fields: [matchId], references: [id])
}
```

### 11.2 Ayanamsha and House-System Switching

The same physical match (same kickoff time, same venue) yields three different charts:

| Engine | Ayanamsha | Houses |
|---|---|---|
| Rao | Lahiri | Whole Sign |
| Chokoisky | Lahiri (Krishnamurti for sublords) | Placidus |
| Frawley | Tropical (none) | Placidus |

The Python microservice must compute all three variants. Use `pyswisseph.swe_set_sid_mode()` to switch ayanamsha between calls. For Frawley's tropical chart, call `swe_set_sid_mode(SE_SIDM_FAGAN)` is WRONG — instead set tropical mode by NOT calling any sid mode (the default).

### 11.3 Reference Tables to Pre-Load

Insert these tables into the database on first run (or hardcode as TypeScript constants):

1. **Rao's planetary friendships** (Rao p.39) — 9×9 matrix
2. **Chokoisky's planet-on-cusp effects** (his table 4.1, p.63–64) — 14 planets × 3 cusp axes
3. **Chokoisky's D9 planet effects** (his table 5.3, p.95–96) — note OPPOSITE effects for Mars, Mercury, Venus
4. **108 Navamsha syllables** (Chokoisky table 7.1, p.142) — 12 signs × 9 navamshas
5. **28 Nakshatras with yogataras and effects** (Chokoisky table 8.1, p.160–161)
6. **Planet dignity table** (Chokoisky table 3.1, p.46) — own sign / exaltation / debilitation / dig bala
7. **Planetary speeds** for station detection (Chokoisky p.47)
8. **Antiscia sign pairs** (Frawley Appendix 1)
9. **Arabian Parts formulas** (only Fortuna = Asc + Moon − Sun; Resignation = Saturn + Jupiter − Sun)
10. **Common national team charts** (England 1066, Brazil 1822, Germany 1871, Italy 1861, Spain 1492, France 843, Argentina 1816, Netherlands 1581, Portugal 1143, etc.)
11. **Common club founding charts** for major leagues
12. **Wikipedia article name disambiguation table** (e.g., "Old Trafford" → "Old Trafford (football)"; "Camp Nou" → "Spotify Camp Nou")

### 11.4 Pre-Built Test Cases (Acceptance Criteria)

The app is correct when these historical matches produce the historically accurate predictions from all three engines:

1. **2014 World Cup: Holland vs Spain** (June 13, 2014, 16:00 local Salvador, Brazil)
   - All 3 engines should predict Holland (underdog) victory
   - Goal differential: ~4 (Holland won 5–1)

2. **2015 IPL Final: Mumbai Indians vs Chennai Super Kings** (May 24, 2015, 20:00 IST Kolkata)
   - Engines should predict Mumbai Indians win (they won by 41 runs)

3. **1998 World Cup: Norway vs Brazil** (group stage)
   - All 3 engines should predict Brazil win
   - Norway's upset victory in this match was an "Astrology Works!" moment for Chokoisky — engines may legitimately disagree here; the app should reflect that disagreement honestly

4. **1999 Champions League Final: Manchester United vs Bayern Munich** (May 26, 1999, 20:45 BST Barcelona)
   - Engines should predict Man Utd win
   - Late-winning-goal indicator should fire (Man Utd scored twice in stoppage time)

5. **A clearly favored match** (e.g., Bayern Munich vs a 3rd-division team in a Cup tie)
   - All 3 engines should agree on the favorite; if any disagrees, the app should show the disagreement prominently rather than mask it

### 11.5 Performance

- Chart computation: < 2 seconds per engine
- Total analysis (all 3 engines in parallel): < 5 seconds end-to-end
- UI render of results: < 1 second after data returns
- Wikipedia venue lookup: < 3 seconds (with timeout → fallback to OSM)
- ML training run (on 1000 matches): < 30 seconds
- Dataset table render with 1000 rows: < 2 seconds (use pagination)

### 11.6 Error Handling

- If the astrology microservice is down, fall back to a "chart unavailable" view that lets the user upload a chart image and manually enter planet positions
- If a team's founding chart is missing, the Rao engine should display "Unable to run Nations' Charts phase — Game Analysis + Planetary Influence still computed" and reduce Rao's confidence accordingly
- If odds are missing or equal, disable Frawley's engine with a clear notice
- If Wikipedia lookup fails or times out, fall back to OSM; if OSM fails, fall back to manual entry with a "Lookup unavailable — please enter coordinates manually" notice
- If the ML model file is missing or corrupted, fall back to equal weights (1.0 per engine) with a banner: "ML model unavailable — using equal-weight synthesis"

---

## 12. Historical Dataset & Machine Learning Subsystem (NEW per user request)

This is the core differentiator of the app. The ML subsystem is **not** a black-box neural network — it is a transparent, auditable feature-combination discovery system that surfaces statistically significant astrological patterns and feeds their weights back into the synthesis layer.

### 12.1 Data Lifecycle

```
User adds match (historical or new) ──▶ Form ──▶ Three engines run ──▶ Verdict saved
                                              │
                                              ├─▶ ML features extracted from chart + verdicts
                                              └─▶ Match record saved with status="pending" or "completed"

For pending matches ──▶ User edits record after match ──▶ Scoreline + status updated
                                                         │
                                                         └─▶ Edit audit recorded; ML features NOT recomputed (chart unchanged)

Nightly ML job (or on-demand retrain) ──▶ Load all completed matches ──▶ Extract features ──▶ Discover combinations ──▶ Train weights ──▶ Save model version ──▶ Activate
```

### 12.2 Feature Extraction

For each completed match, extract a feature vector. Features are **structured and interpretable** — no raw pixel data, no opaque embeddings. Each feature can be described in plain English.

**Engine agreement features**:
- `rao_verdict` ∈ {A, B, draw}
- `chokoisky_verdict` ∈ {A, B, draw}
- `frawley_verdict` ∈ {A, B, draw, disabled}
- `engine_agreement_count` ∈ {0, 1, 2, 3}
- `agreement_pattern` ∈ {"all_agree", "rao_chokoisky_agree", "rao_frawley_agree", "chokoisky_frawley_agree", "all_disagree"}

**Per-engine quantitative features** (each is a numeric value):
- `rao_point_differential` (Native − Rival, e.g., +5 means favorite wins by 5)
- `chokoisky_total` (signed total from multi-tier system)
- `chokoisky_d9_cusp_strong_planet_present` (boolean)
- `chokoisky_sky_present` (boolean)
- `chokoisky_sublord_dominance` (signed total of sublord point diff)
- `frawley_testimony_count`
- `frawley_lord_on_enemy_cusp` (boolean, strongest testimony)
- `frawley_moon_final_aspect_late` (boolean, late-goal indicator)
- `frawley_pluto_on_1st_cusp` (boolean, upset indicator)

**Astrological configuration features** (the interesting ones for pattern discovery):
- `d9_jupiter_on_favorite_cusp` (boolean)
- `d9_saturn_on_favorite_cusp` (boolean)
- `d9_mars_on_either_cusp` (boolean — Mars is negative in D9)
- `lord_1_on_7th_cusp_tropical` (boolean — Frawley's strongest testimony)
- `lord_7_on_1st_cusp_tropical` (boolean)
- `antiscion_fortuna_on_1st_or_7th_cusp` (boolean)
- `moon_final_aspect_to` ∈ {Lord1, Lord7, Lord10, Lord4, none}
- `rao_saturn_in_8th_nation_chart` (boolean, interruption indicator)
- `rao_planetary_influence_included` (boolean — was captain data provided)
- `rao_captain_jersey_match_date_relation` ∈ {friend, neutral, enemy}
- `nama_pad_a_match` (boolean — Team A name syllable on MC)
- `nama_pad_b_match` (boolean)
- `planetary_war_winner_team` ∈ {A, B, none}
- `major_tara_on_significator` ∈ {Regulus_A, Regulus_B, Pollux_A, Pollux_B, Vega_A, Vega_B, none}
- `sandhi_window_active` (boolean)

**Match context features**:
- `sport` ∈ {football, american_football, cricket, ...}
- `context` ∈ {league, knockout, final, friendly}
- `draw_possible` (boolean)
- `odds_differential` (|oddsA − oddsB|)

**Outcome features** (the labels for training):
- `actual_winner` ∈ {A, B, draw}
- `actual_scoreA` (int)
- `actual_scoreB` (int)
- `actual_goal_diff` (|scoreA − scoreB|)
- `actual_interrupted` (boolean)

### 12.3 Combination Discovery Algorithm

The ML pipeline discovers **astrological combinations** that have statistically significant predictive power. This is NOT a deep learning model — it is a transparent, interpretable feature-engineering approach.

**Algorithm**:

```
1. Load all completed matches with engine verdicts.
2. For each pair (and triple) of features, compute the conditional accuracy:
   - Among matches where (feature1=X AND feature2=Y), what fraction had the same predicted winner as actual winner?
3. Keep combinations where:
   - Sample size ≥ 10 (configurable; raise to 20 after dataset >500 matches)
   - Accuracy ≥ 65% (configurable; raise to 70% after dataset >500 matches)
   - The combination is statistically significant (chi-squared test p < 0.05)
4. For each kept combination, compute its weight:
   weight = 1.0 + (accuracy - 0.5) * 2.0
   (so 50% acc = weight 1.0, 75% acc = weight 1.5, 100% acc = weight 2.0)
5. Cap weight at 3.0 to prevent any single combination from dominating.
6. Persist combinations to MLCombination table with their weights.
```

**Combination types to evaluate** (3 categories):

**Category A — Engine agreement patterns** (most useful in early dataset):
- "rao_chokoisky_agree" → accuracy of that agreement pattern
- "all_three_agree" → accuracy when all three engines agree
- "frawley_disagrees_with_other_two" → accuracy of upset prediction

**Category B — Strong astrological features** (Chokoisky's most powerful testimonies):
- "d9_jupiter_on_favorite_cusp" alone
- "lord_1_on_7th_cusp_tropical" alone
- "sublord_dominance > 9" alone
- "rao_point_diff > 8" alone
- These single-feature rules become baselines; the algorithm then looks for two-feature combinations that improve on them

**Category C — Two and three feature combinations**:
- "rao_chokoisky_agree AND d9_jupiter_on_favorite_cusp"
- "frawley_lord_on_enemy_cusp AND NOT rao_saturn_in_8th"
- "chokoisky_sublord_dominance > 9 AND rao_point_diff > 5"
- Three-feature combinations only evaluated after dataset >200 matches

### 12.4 Weight Application in Synthesis

When a new match is analyzed:

1. Extract its features.
2. Check which MLCombinations match this match's feature vector.
3. For each matching combination, look up its weight.
4. Compute a `confidence_multiplier`:
   - If no combinations match → 1.0 (use baseline synthesis)
   - If combinations match → 1.0 + Σ(combination_weights) / 3.0 (capped at 2.0)
5. Apply this multiplier to the consensus confidence per §8.2.
6. Store the matching combination IDs in `Match.mlPatternMatches` for auditability.

**Example**: A new match has features matching two combinations:
- "rao_chokoisky_agree" (weight 1.4, historical accuracy 78%)
- "d9_jupiter_on_favorite_cusp" (weight 1.6, historical accuracy 82%)
- Confidence multiplier = 1.0 + (1.4 + 1.6) / 3.0 = 1.0 + 1.0 = 2.0
- This multiplier is applied to the base consensus confidence (e.g., 65% × 2.0 = capped at 100%)

The ML insight banner on the results page displays: "📊 Historical pattern: 2 matching combinations, combined weight 3.0, average historical accuracy 80%."

### 12.5 Cold Start & Growth Milestones

| Completed matches | ML behavior |
|---|---|
| 0–29 | Equal weights (1.0 each engine). No combinations computed. Banner: "ML cold start — equal weights." |
| 30–99 | Single-feature combinations only. Min sample 10, accuracy threshold 65%. |
| 100–499 | Two-feature combinations enabled. Min sample 15, accuracy threshold 70%. |
| 500+ | Three-feature combinations enabled. Min sample 20, accuracy threshold 75%. Nightly retraining strongly recommended. |

### 12.6 Training Pipeline (Python)

```
POST /ml/train (Python microservice)
1. Query all Match records with status="completed" and all three verdicts present.
2. For each match, extract the feature vector.
3. Build a pandas DataFrame.
4. Run combination discovery (per §12.3):
   - For each candidate combination, slice the DataFrame and compute accuracy.
   - Apply statistical significance test (chi-squared).
5. Save qualifying combinations to MLCombination table.
6. Save a new MLModelVersion with overall and per-engine accuracies.
7. Mark the new version as current.
8. Return summary: { matchesTrained: N, combinationsDiscovered: K, overallAccuracy: A, previousAccuracy: B }
```

Use `scikit-learn` for the chi-squared test, `pandas` for the DataFrame operations, `joblib` to persist a snapshot of the trained model artifact (even though the "model" is really a list of weighted combinations, persisting it as a joblib pickle allows for fast loading).

### 12.7 Edit & Audit Flow (NEW per user request)

When a user edits a match record (e.g., adds a scoreline to a pending match):

1. Save the current state of all changed fields to `EditAudit` records (field name, old value, new value, timestamp, user).
2. Update the Match record.
3. If `scoreA` and `scoreB` were added (transitioning from null → integer), set `status="completed"`.
4. **Do NOT recompute engine verdicts** (chart inputs didn't change) — the original verdicts stand.
5. If the user changed input fields (kickoff time, venue, team, etc.) that affect the chart, prompt: "Input changes will require re-analysis. Re-run engines now? (Yes / Save changes without re-run / Cancel)"
   - "Yes" → recompute charts, re-run engines, save as a new analysis version (preserve old version in `analysisVersions` array)
   - "Save without re-run" → save input changes only; mark the record with `stale_analysis=true` flag
6. If `status` becomes `completed`, the next ML training run will include this match.

### 12.8 Adding Historical Matches (NEW per user request)

When a user adds a historical match (a match that already happened, with scoreline known):

1. User fills the form with all the same inputs as for a new match.
2. User also fills the Scoreline section (Team A final score, Team B final score, status).
3. On submit, the three engines still run (so the user can see what the engines WOULD have predicted).
4. The Match record is saved with `status="completed"` and `postHocAnalysis=true`.
5. The ML training pipeline will include this match but the post-hoc flag is preserved — if the dataset shows that post-hoc analyses have systematically different accuracy than real-time ones, the ML pipeline can downweight post-hoc samples in training (configurable; default: include with weight 0.5).

### 12.9 Adding New Matches for Analysis (NEW per user request)

When a user adds a new (upcoming) match:

1. User fills the form (no scoreline section).
2. On submit, the three engines run and the verdicts are saved.
3. The Match record is saved with `status="pending"`.
4. After the match is played, the user returns to the record and either:
   - Edits it to add the scoreline (per §12.7), or
   - Uses the "Mark result" quick-action modal on the dataset page.
5. Status transitions to `completed`; the next ML training run includes this match.

### 12.10 ML Dashboard — Manual Retrain & Rollback

From the ML dashboard (Page 5):

- "Retrain now" button: triggers a synchronous training run; shows a progress bar; on completion, displays a summary comparing the new model's accuracy to the previous model's.
- "Rollback to previous model" dropdown: lists the last 10 model versions with their overall accuracy and the timestamp of training. Selecting one and confirming:
  - Marks the selected version as current.
  - Marks all later versions as inactive (not deleted — preserved for audit).
  - The selected version's combinations become the active weights.
- "Nightly retrain" toggle: schedules a job (via APScheduler) to run at 02:00 local time, retraining on all completed matches added since the last training run.

### 12.11 Privacy & Data Integrity

- All match records are immutable once `status="completed"` (no edits to scoreline or status after completion; only notes and non-input metadata can be edited).
- All edits are logged to EditAudit for full traceability.
- The ML training set is reproducible: any past model version can be re-derived from the historical dataset at that point in time (since the dataset is append-only for completed matches and edit audits preserve field history).
- If a match is discovered to have incorrect data (e.g., wrong kickoff time), the user can:
  - Edit the input fields (which flags `stale_analysis=true` and prompts re-run per §12.7), or
  - Soft-delete the record (admin only) — preserves audit trail but excludes from ML training.

---

## 13. Suggested First-Prompt For the LLM Coding Agent

When you start a fresh session with the LLM coding agent (ChatGPT, Claude, Cursor, etc.), open with this:

> I'm building a Next.js 16 + Python FastAPI web application that performs astrological analysis of football matches using three distinct methodologies from three reference books. The app also functions as a living research instrument with a historical dataset, ML-based discovery of predictive astrological combinations, and full CRUD for match records (add historical, add new, edit scorelines after games).
>
> I have a complete specification document. I'd like to build this in stages:
>
> **Stage 1**: Scaffold the Next.js app, the Python FastAPI microservice, and the PostgreSQL database schema (Prisma). Set up the match-setup form with all 17 inputs including the optional captain/jersey toggle and Wikipedia-based stadium lookup with manual override.
>
> **Stage 2**: Implement the Wikipedia stadium coordinate lookup (with OSM fallback and manual override), and the Python astrology microservice using `pyswisseph` — D1 chart, D9 navamsha, Placidus + Whole Sign cusps, antiscia, Krishnamurti sublords, all three ayanamsha modes.
>
> **Stage 3**: Implement Engine 1 (Rao's Inclusive Methodology) per §5 of the spec, including the optional Planetary Influence layer.
>
> **Stage 4**: Implement Engine 2 (Chokoisky's Gambler's Dharma) per §6 of the spec — this is the most complex engine.
>
> **Stage 5**: Implement Engine 3 (Frawley's Event Chart method) per §7 of the spec.
>
> **Stage 6**: Build the comparative-outlook synthesizer per §8 and the analysis dashboard per §9.1, §9.2.
>
> **Stage 7**: Build the Historical Dataset browser (§9.3), Match Record Detail & Edit page (§9.4), and the Edit & Audit flow per §12.7.
>
> **Stage 8**: Implement the ML pipeline: feature extraction (§12.2), combination discovery (§12.3), weight application in synthesis (§12.4), training endpoint (§12.6), and ML Training Dashboard (§9.5).
>
> **Stage 9**: Build the Settings page (§9.6) and the Detailed Chart View drill-down (§9.7).
>
> **Stage 10**: Add the sandhi guardrails, anti-betting notice, equal-odds block, and post-hoc analysis caveats per §10.
>
> **Stage 11**: Validate against the test cases in §11.4 and verify performance budgets in §11.5.
>
> I will paste the full specification document next. Confirm you understand the staging and that you should ask me before making any architectural decisions not covered in the spec.

Then paste this entire document.

---

## 14. Reference Books (Source of Truth)

If any technique in this spec is ambiguous, consult the source books:

1. **Rao, Ravi.** *Sports Astrology: The Inclusive Methodology of Game Analysis.* Star Publication House, 2017. ISBN 978-81-929358-0-5. — Especially §3 "Inclusive Methodology of Sports Astrology" and the case studies in §2 (World Cup 2015), §3 (T20), §4 (IPL).

2. **Chokoisky, Simon.** *Gambler's Dharma: Sports Betting with Vedic Astrology.* Destiny Books, 2017. ISBN 978-0-9539774-2-0. — Chapters 3–8 for techniques, appendices 1–3 for sublord tables and tara balam.

3. **Frawley, John.** *Sports Astrology.* Apprentice Books, 2007. ISBN 978-0-9539774-2-0. — Chapter 2 "The Chart for the Event" is the primary source; Chapter 4 on profit horary is NOT used in this app.

These books are the authoritative source. Where this spec and a book disagree, the book wins.

---

**End of specification. Build the app.**
