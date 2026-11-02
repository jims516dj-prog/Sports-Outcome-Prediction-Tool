# Sports Outcome Prediction Tool

Two projects, built and tested against more than 70,000 real matches.

| Folder | What it is |
|---|---|
| [`sportspredict/`](sportspredict/) | Statistical match predictor for soccer, basketball, ice hockey and tennis, run from the command line. It covers match results and soccer over/under 2.5 goals, with a confidence filter that flags picks which were historically at least 70% right. It also has tests of whether Western/Vedic astrology and numerology add any predictive value. |
| [`astro-football/`](astro-football/) | Web app built from the *Astrological Football Match Analyzer* specification (`astro-football/astrological-football-analyzer-prompt.md`). Three classical sports-astrology engines (Rao, Chokoisky, Frawley), a comparative outlook, a historical dataset and ML pattern discovery. Next.js 16 + PostgreSQL + a Python/Swiss Ephemeris service. |

## Headline results (out-of-sample, season by season)

| Test | Result |
|---|---|
| NBA 1995–2015, match result | 67.7% on all games (FiveThirtyEight's Elo: 67.5%) |
| International soccer 2005–2025, home/draw/away | 59.3% on all; 70.3% on the 58% of matches the filter flags |
| English, Spanish and German top leagues 2015–20, home/draw/away | 52.6% on all; 70.7% on the 26% flagged |
| Over/under 2.5 goals | 59.2% (international), 54.8% (club leagues) |
| Astrology and numerology features | no reliable gain in any test |
| Rao / Chokoisky / Frawley engines, 23,701 matches with real kickoff times | 34% / 33% / 40%, against 52.6% for backing the favourite; adding them made the model slightly worse |

Details, methods and caveats are in each folder's README.

## Quick start

Download the public datasets and ephemeris files into `data/` (about 35 MB, not committed):

```bash
bash scripts/fetch_data.sh
```

Statistical predictor:

```bash
cd sportspredict && pip install -r requirements.txt
```

```bash
python predict.py soccer intl examples/intl_fixtures.csv
```

The web app needs Node 20+, PostgreSQL and Python 3.11+; see [`astro-football/README.md`](astro-football/README.md).

## Data sources

martj42/international_results, FiveThirtyEight `nba-elo`, footballcsv and openfootball
`football.json` (match data), and the Swiss Ephemeris files from aloistr/swisseph. The Swiss
Ephemeris is dual-licensed (AGPL or a commercial licence from Astrodienst).

> For research and education. These tools are not betting advice: the betting market already prices in the same favourites.
