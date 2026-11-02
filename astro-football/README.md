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
│   ├── wikipedia_geo.py         Wikipedia → OpenStreetMap stadium lookup, timezone conversion
│   └── main.py                  routes + APScheduler nightly retrain
└── scripts/
    ├── dev.sh                   start both services
    └── import_history.py        bulk-import historical matches through the API
```

## Setup

Requirements: Node 20+, Python 3.11+, PostgreSQL 14+.

```bash
npm install
```

```bash
cp .env.example .env    # adjust DATABASE_URL if needed
```

```bash
createdb astro_football && npx prisma db push && npm run db:seed
```

```bash
python -m venv .venv && .venv/bin/pip install -r services/python-astro/requirements.txt
```

Ephemeris files (`sepl_18.se1`, `semo_18.se1`, `seas_18.se1`, `sefstars.txt`) live in
`services/python-astro/ephe/` (set `SE_EPHE_PATH` to move them). They are needed for Chiron,
Ceres and the fixed stars; the planets fall back to the built-in Moshier ephemeris.

Run both services:

```bash
PYTHON=.venv/bin/python npm run dev:all
```

Then open http://localhost:3000. The Python service listens on port 8001 (`ASTRO_SERVICE_URL`).

### Importing history (optional)

```bash
.venv/bin/python scripts/import_history.py --data path/to/openfootball --from 2023-07-01
```

This reads openfootball `football.json` season files (with kickoff times) and posts each
match through `POST /api/matches` as a historical, post-hoc record. That source has no
bookmaker odds, so odds are derived from an Elo rating and each record's notes say so.

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
