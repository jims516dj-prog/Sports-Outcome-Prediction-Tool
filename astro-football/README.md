# Astrological Football Match Analyzer

A research instrument that analyses football matches with three classical sports-astrology
methods, reconciles them into a comparative outlook, and tests them against a growing
historical dataset. It is built from the supplied build specification
(`astrological-football-analyzer-prompt.md`).

| Engine | Source | Chart |
|---|---|---|
| Rao — Inclusive Methodology | Dr. Ravi Rao, *Sports Astrology* (2017) | sidereal (Lahiri), whole sign |
| Chokoisky — Gambler's Dharma | Simon Chokoisky, *Gambler's Dharma* (2017) | sidereal (Lahiri; Krishnamurti for sublords), Placidus, D1 + D9 |
| Frawley — Event Chart | John Frawley, *Sports Astrology* (2007) | tropical, Placidus |

> **For astrological research and educational purposes only — not betting advice.** The
> disclaimer banner (spec 10.1) is on every page and cannot be dismissed.

## Architecture

```
astro-football/
├── app/                         Next.js 16 App Router pages + API routes
│   ├── page.tsx                 dashboard
│   ├── analyze/                 match-setup form → three-engine analysis
│   ├── dataset/                 historical dataset browser, /new, /[id] (detail, edit, timeline), /[id]/chart
│   ├── ml/                      ML training dashboard
│   ├── sync/                    data sync: past seasons, upcoming fixtures, results
│   ├── settings/                reference data, toggles, ML configuration, reference tables, admin mode
│   └── api/                     chart, rao, chokoisky, frawley, stadium-lookup, tz, matches (+ export,
│                                reanalyze, result), teams, venues (+ reverify), aliases, settings,
│                                reference, stats, natal, ml/{train,weights,metrics,rollback,schedule,combination}
├── components/                  UI (form, results dashboard, chart wheel, dataset table, ML dashboard, settings)
├── lib/
│   ├── analysis.ts              builds the service request, runs the engines, applies ML weights
│   ├── ml/                      feature_extractor, combination_discoverer, weights_provider
│   └── dataset/                 crud (create / edit + audit / versions / soft delete), query (SQL filters)
├── prisma/schema.prisma         PostgreSQL schema (spec 11.1 + small additions, see below)
├── prisma/seed.mjs              founding charts, stadiums, Wikipedia aliases
├── services/python-astro/       FastAPI service
│   ├── chart.py                 Swiss Ephemeris charts: three variants, D9, KP sublords, antiscia, Gulika, Upaketu
│   ├── engines.py               Rao, Chokoisky, Frawley engines, sandhi guardrails, synthesis
│   ├── reference.py             reference tables
│   ├── ml_pipeline.py           feature extraction, combination discovery, training
│   ├── sources.py               openfootball + football-data.org fixtures/results, Elo odds
│   ├── teams.py                 club names, stadium coordinates, timezones
│   ├── wikipedia_geo.py         Wikipedia → OpenStreetMap stadium lookup, timezone conversion
│   └── main.py                  routes + APScheduler nightly retrain
└── scripts/
    ├── dev.sh                   start both services
    └── import_history.py        bulk-import historical matches through the API
```

## Setup

Requirements: Node 20+, Python 3.11 (the `pyswisseph` installers stop at 3.11; newer
versions need a C compiler), PostgreSQL 14+.

Create the database user and database that `.env.example` points to. Use your Postgres admin
login: `postgres` on most installs, your own username with Homebrew on macOS.

```bash
psql -U postgres -c "CREATE USER astro WITH PASSWORD 'astro' CREATEDB;"
```

```bash
psql -U postgres -c "CREATE DATABASE astro_football OWNER astro;"
```

Install the web app and create the tables (on Windows, `copy` instead of `cp`):

```bash
npm install
```

```bash
cp .env.example .env
```

```bash
npx prisma db push && npm run db:seed
```

Install the Python service into `.venv` (on Windows:
`.venv\Scripts\pip install -r services\python-astro\requirements.txt`):

```bash
python3.11 -m venv .venv
```

```bash
.venv/bin/pip install -r services/python-astro/requirements.txt
```

Ephemeris files (`sepl_18.se1`, `semo_18.se1`, `seas_18.se1`, `sefstars.txt`) live in
`services/python-astro/ephe/` (set `SE_EPHE_PATH` to move them). They are needed for Chiron,
Ceres and the fixed stars; the planets fall back to the built-in Moshier ephemeris.

### Run

macOS / Linux, both services with one command (uses `.venv` automatically; Ctrl+C stops both):

```bash
npm run dev:all
```

Windows, or to run them separately, use two terminals. First the Python service
(on Windows, `..\..\.venv\Scripts\python` instead):

```bash
cd services/python-astro && ../../.venv/bin/python -m uvicorn main:app --port 8001
```

Then the website, from the `astro-football` folder:

```bash
npm run dev
```

Open http://localhost:3000. The dashboard shows "Astrology service: online" when both are
running. The Python service listens on port 8001 (`ASTRO_SERVICE_URL`).

## Data sync: past games, upcoming fixtures and results

Open **Data sync** in the app.

- **Past games:** choose leagues and seasons, then click **Import**. Finished matches with real
  kickoff times come from openfootball (Premier League and Bundesliga from 2010-11, La Liga from
  2012-13, Serie A from 2013-14, Ligue 1 and the Championship from 2014-15, Eredivisie and Primeira
  Liga from 2018-19). They are stored as historical (post-hoc) records for the ML model. Matches
  already in the dataset are skipped, so re-running is safe.
- **Upcoming games & results:** **Refresh now** adds fixtures in the next 14 days as pending
  matches, analysed straight away. It records the score of each pending match once it has
  finished, moves rescheduled games (re-running their analysis), flags postponed ones, and adds
  missing finished games from the last 45 days.
  - The refresh also runs automatically every 6 hours while the app is running.
  - The ML model retrains after any sync that adds results.
  - Every setting is on the page, and every automatic change appears in the match's edit
    timeline as `auto-sync`.
- **Faster results:** openfootball is community-maintained and can be weeks behind. A free
  football-data.org API key (pasted on the page) adds exact UTC kickoff times and results within
  minutes of full time for the same leagues.
- **Odds:** neither source has bookmaker odds, so each match gets odds derived from an Elo rating,
  and its notes say so. You can edit the odds on any pending match; changing them offers to
  re-run the analysis.
- **Kickoff times:** a fixture without a published kickoff time is added on a later refresh, once
  the time is known, because charts are cast for the kickoff minute.

Downloaded seasons and looked-up stadiums are cached in `services/python-astro/cache/`.

### Updating an existing installation

After getting a newer version, run these in the `astro-football` folder. They add new database
columns without touching your data, and install any new packages.

```bash
npm install
```

```bash
npx prisma db push
```

```bash
.venv/bin/pip install -r services/python-astro/requirements.txt
```

On Windows the last command is `.venv\Scripts\pip install -r services\python-astro\requirements.txt`.

`scripts/import_history.py` (command-line bulk import from downloaded files) still works; the
Data sync page replaces it for most uses.

## How the spec is met

- **Form (3):** four core inputs, then a collapsible layout:
  - Team autocomplete with founding-chart and home-venue autofill.
  - Venue lookup: Wikipedia, then OpenStreetMap, then manual entry, with source tags and a saved venue cache.
  - Live GMT → local preview (DST-aware), and local → GMT entry for historical matches.
  - Odds with favourite detection and the equal-odds (±0.05) block.
  - Founding charts.
  - Optional captain/jersey toggle.
  - Scoreline section.
  - Non-blocking sandhi warnings, and both submit buttons.
- **Charts (4):** every analysis computes all three chart variants. Pre-1582 founding dates use the Julian calendar.
- **Engines (5–7):**
  - Each emits per-parameter or per-technique tables, markdown reasoning, testimonies with strengths, a verdict, a goal range, a confidence and caveats.
  - The ML features from section 12.2 come out of every analysis.
- **Synthesis (8):**
  - Weighted consensus, disagreement analysis and the intersected goal range.
  - The confidence score.
  - The ML multiplier (12.4), the historical-pattern banner and observations.
- **Dataset (9.3/9.4, 12.7–12.11):**
  - Server-side filters, sorting and pagination.
  - Per-row actions: view, edit, mark result, re-analyze, soft delete (admin).
  - CSV and JSON export.
  - An edit audit timeline and analysis versions; earlier verdicts are preserved.
  - Re-run / save-without-re-run / cancel on input changes, with stale flagging.
  - Completed records keep their scoreline locked.
  - Post-hoc tagging, weighted 0.5 by default.
- **ML (12):**
  - Milestone thresholds (cold start under 30 matches, then 1-, 2- and 3-feature combinations).
  - Chi-squared filter and the weight formula.
  - Model versions with joblib artifacts, rollback, nightly 02:00 retraining, and per-engine accuracy over 30/60/90 days.
- **Guardrails (10):**
  - Banner.
  - Sandhi: eclipse ±3 days, sankranti, sunrise/sunset ±30 min, stations ±24 h, Moon void of course.
  - Equal-odds block, Rao interruption caveat, post-hoc caveat.

### Additions and departures (deliberate)

- **Favourite baseline and holdout check on every ML pattern.** The dashboard shows how often simply backing the favourite was right in the same matches, and re-mines patterns on the oldest 70% of matches to score them on the newest 30%.
  - Why: in a 23,701-match backtest the three methods scored 33–40% against 52.6% for backing the favourite. Patterns mined on small samples at 73% fell to about 50% on new matches.
  - These columns let the dashboard tell real signal from chance. The spec's own algorithm and weights are applied unchanged.
- **Book tables.** The cited book tables were not available. Standard classical tables stand in, and each is labelled on Settings → Reference tables:
  - Parashari friendships for Rao p.39.
  - Avakahada pada syllables for Chokoisky table 7.1.
  - Classical dignities for table 3.1.
- **Rao's 0–3 scoring.** Rao's judgement is turned into a fixed rule: natural benefic/malefic influence, friendship with the house lord, and dignity.
- **Fixed stars.** Positions are computed live from the Swiss Ephemeris catalogue. The spec's Algol position (26° Taurus) is tropical, so the engine uses the computed sidereal position instead.
- **Book quotations.** Engine cards show a *paraphrased* method note instead of a quotation, because the books were not available to quote. The only quotation is Rao's, which the spec supplies.
- **Schema additions:**
  - `staleAnalysis` and `deleted` on Match.
  - `synthesis`.
  - `modelVersionId`, `favouriteBaseline` and `holdoutAccuracy` on MLCombination, which rollback needs.
  - `engineWeights` and `metrics` on MLModelVersion.
  - `Setting` and `WikiAlias` tables.
- **No authentication.** Admin mode is a local browser flag (Settings → Admin). Add real authentication before exposing the app.
- **No shadcn registry.** The shadcn-style primitives in `components/ui.tsx` are hand-written, and the chart wheel is plain SVG; neither needs d3 or the shadcn registry.

## Verified here

- **Spec acceptance cases (11.4):** all five run end to end. The engines do *not* all reproduce the spec's expected verdicts, and the app shows those disagreements openly as the spec asks.
- **Import:** 3,484 matches from the 2023–25 top-five-league seasons imported in about 1 minute.
- **Training:** about 1 second on 3,489 matches. The consensus scored 34.6% against a 52.8% favourite baseline.
- **Analysis speed:** about 100 ms per match after warm-up.
- **Build:** `next build` passes, and a browser walk-through of every page shows no console errors.
- **Not tested:** the Wikipedia and OpenStreetMap lookups. Both are implemented, but those hosts were blocked in the build environment, so only the manual and seeded-venue paths were exercised.
