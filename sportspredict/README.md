# sportspredict: pre-match outcome predictor (soccer, ice hockey, tennis, basketball)

A statistical / machine-learning engine with a full Western + Vedic astrology and
Pythagorean numerology feature module. Every feature is **tested, not assumed**:
models are scored walk-forward (trained only on the past, predicting the next
season), and the esoteric features face an ablation plus a permutation test.

## What it uses (all available before kick-off)
| Group | Features |
|---|---|
| Strength ratings | Elo with home advantage, margin-of-victory multiplier, between-season regression; surface-specific Elo (tennis) |
| Scoring model | Online Poisson attack/defence model giving P(home/draw/away) and expected goals (soccer, hockey); points-margin rating (basketball) |
| Form & schedule | EWMA results form, EWMA goal/point-difference form, rest days, back-to-backs, experience, neutral venue, friendly vs competitive |
| Betting market | De-margined implied probabilities from odds, if supplied (usually the single strongest pre-match signal) |
| Western astrology | Moon phase, Moon sign polarity, Mercury/Mars retrograde, natal Sun vs transiting Sun/Moon/Mars aspects (needs founding date / DOB) |
| Vedic astrology | Sidereal (Lahiri) Moon, nakshatra, tithi (Rikta tithis), weekday lord, Tara Bala, Chandra Bala (needs DOB / founding date) |
| Numerology | Name number vs universal day, friendly-number harmony, life path, personal day |

Ephemeris is computed in `esoteric.py` (Meeus Sun/Moon + JPL Keplerian planets),
verified against known 2024–25 Mercury/Mars retrogrades, full moons and ingresses.

## Measured results (walk-forward, out-of-sample)
| Dataset | Matches tested | Accuracy, all matches | Most-confident 50% | Most-confident 30% | Confidence filter targeting 70% (threshold set on past seasons only) |
|---|---|---|---|---|---|
| NBA 1995–2015 | 25,927 | **67.7%** (538 Elo: 67.5%) | 77.6% | 82.5% | 69.7% on 85% of games |
| International soccer 2005–2025 (3-way) | 21,002 | **59.3%** | 73.7% | 81.1% | 70.3% on 58% of matches |
| EPL/La Liga/Bundesliga 2015–2020 (3-way) | 5,894 | **52.6%** | 63.9% | 71.2% | 70.7% on 26% of matches |

### Over/under 2.5 goals (soccer)
Model: logistic regression on the Poisson goal model's expected goals (P(total > 2.5)
from λ_home + λ_away), each team's recent total-goals tempo, goals-for × goals-against
interaction, the competition's rolling scoring level, mismatch size |λh − λa|,
friendly flag, and de-margined over/under odds if you supply `odds_over, odds_under`.

| Dataset | Matches | Over rate | Always pick the more common side | Poisson only | **Model** | Most-confident 20% | 70% target, cut-off set from past seasons only |
|---|---|---|---|---|---|---|---|
| International 2005–2025 | 21,002 | 49.0% | 51.0% | 59.0% | **59.2%** | 70.6% | 70.4% on 20% of matches |
| EPL/La Liga/Bundesliga 2015–2020 | 5,894 | 52.8% | 52.8% | 55.2% | **54.8%** | 64.4% | 68.1% on 8.5% (target missed) |

Club over/under is close to a coin flip without shot/xG data; bookmakers reach about
55–57%. Strategy: bet only `HIGH-CONFIDENCE` picks, and in club leagues treat even
those as marginal unless you add odds or xG history. In internationals most of the
edge comes from mismatches (strong side expected to score 3+), which favour OVER.
Astrology/numerology (Moon phase, tithi, retrogrades, combined natal "energy" of
both sides) again added nothing: log-loss +0.0010 club / +0.0002 international,
permutation p = 0.64 for both.
Hockey uses the same machinery with a 5.5 line (`--ou-line` to change it).

Tennis and NHL code paths are implemented and smoke-tested on synthetic data only:
no real tennis/NHL dataset was reachable from the build environment. Run
`backtest.py` on your own file to get real numbers.

### Did astrology / numerology help?
| Dataset | Log-loss change from adding esoteric features | Permutation p | Esoteric-only model vs always picking the most common result |
|---|---|---|---|
| Club soccer | +0.0022 (worse; 95% CI excludes 0) | 0.82 | +0.0 pts |
| International soccer | +0.0002 (worse; CI spans 0) | 0.09 (10 perms) | +0.0 pts |
| NBA | −0.0002 (≈ +0.08 pts accuracy) | 0.016 (60 perms) | +0.02 pts |

The only nominal signal (NBA) came from "Mars retrograde", which acts as a proxy
for the multi-year decline in home advantage, and "martial weekday lord", which
is Tue/Sat/Sun: NBA home teams win more on weekends. Both are scheduling and era
effects, not astrology. **Conclusion: the esoteric features carry no usable
predictive information, so they are off by default** (`--esoteric` turns them on).
Natal-chart features (Tara/Chandra Bala, transits) switch on automatically when
`home_birth`/`away_birth` are supplied, and the same test harness will judge them.

## Classical sports-astrology engines (Rao, Chokoisky, Frawley)
`astro_engines.py` implements the three methods from the supplied build specification,
cast with the Swiss Ephemeris for the exact kickoff time and stadium location:

| Engine | Chart | Techniques implemented |
|---|---|---|
| Rao, *Inclusive Methodology* | Sidereal (Lahiri), whole-sign | 0–3 points for Ascendant, Asc lord, Score (10th/4th), Game+Coach (5th+3rd / 11th+9th), Fans & Odds, Penalties; graha drishti, dignity, natural friendships; optional nation/club Moon transposition with the Saturn-on-8th interruption caveat |
| Chokoisky, *Gambler's Dharma* | Sidereal (Lahiri; KP for sublords), Placidus, D1 + D9 | Victory houses, SKY/PKY, D1 cuspal strength (1/7, 4/10, 6/12), D9 cuspal strength (reversed Mars/Mercury/Venus), nama pada (MC navamsha syllable), KP sublords of cusps 1 and 7, nakshatra taras (Regulus, Pollux, Vega, Spica…), planetary war; Upaketu, Gulika, outer planets, Chiron, Ceres |
| Frawley, *Sports Astrology* | Tropical, Placidus | Lords 1/4/7/10 on or just inside cusps (body and antiscion, retrograde rules), Moon placement, antiscion of Fortuna, Moon's last applying aspect within 5° and its sign (Fortuna aspects final, conjunctions final), lords to Fortuna, dispositor of Fortuna, nodes, combustion/cazimi, Pluto, Saturn, Uranus, default-to-favourite rule, late-goal flag |

Plus the spec's synthesis (weighted vote, agreement pattern, 0–100 confidence) and
sandhi flags (eclipse ±3 days, sankranti, sunrise/sunset ±30 min, stations ±24 h).

**Departures from the books (unavoidable here):** the cited book tables were not
available, so standard classical tables are used: Parashari friendships (Rao p.39),
Avakahada pada syllables (Chokoisky table 7.1), classical dignities (table 3.1). Rao's
"benefic/malefic influence → 0–3 points" judgement is turned into a fixed rule.
Chokoisky's stolen cusps, "double whammy" and sublord array are not implemented.
Moon void-of-course is not flagged. The favourite (1st house) comes from the model's
pre-match ratings because the dataset has no odds; that agrees with the bookmaker
favourite in the large majority of matches. Rao's nation/club charts and captain
jersey layer were not tested: no founding times or captain data were available.

### Backtest: 23,701 matches with real kickoff times (EPL, Bundesliga, La Liga, Serie A, Ligue 1, 2010–2025)
`python astro_backtest.py` (openfootball data; venue = home club's stadium; out-of-sample 2012–2025)

| Test | Result |
|---|---|
| Always pick the favourite | **52.6%** |
| Rao / Chokoisky / Frawley accuracy | 34.0% / 32.9% / 40.2% |
| Consensus (all matches) / when all 3 agree | 36.3% / 34.5% |
| Match result: statistics → + all engine features | 52.6% → 52.3%; log-loss +0.0041 (worse; 95% CI excludes 0); permutation p = 0.95 |
| Over/under 2.5: statistics → + engine features | 56.2% → 55.8%; log-loss +0.0011 (worse); permutation p = 0.62 |
| When an engine picks the **underdog** (the real test of an edge) | underdogs won 22.6% (Rao), 22.2% (Chokoisky), 21.7% (Frawley) vs 22.2%, 22.4% and 21.3% the statistics already expected; no difference (p 0.35–0.71) |
| Engine features alone | 46.1% vs 44.5% majority, but identical (46.1%) when the charts are shuffled across matches, so the gain only reflects which side is the favourite |
| Spec §12.3 pattern mining, mined on past seasons and scored on the next | 0 qualifying combinations in 11 of 13 seasons; the 2 found flagged 5 matches in total |
| Same mining on 100-match datasets (spec's early-stage thresholds) | about 4 "significant" patterns per run at 73% in-sample, falling to 50% on new matches, below picking the favourite (53%) |

The engines pick the underdog in about half of all matches (Rao 54%, Chokoisky 52%),
yet underdogs win only 22%. That is why each engine scores below simply backing the
favourite. One of 12 calibration tests reached p < 0.05 (Rao draw picks, p = 0.03),
which is about what chance predicts for 12 tests, and it is not significant after
correcting for multiple tests. **Conclusion: the three methods carry no information
about match results or goal totals beyond what the statistics already contain.**
The spec's pattern mining would mainly surface chance patterns, especially while
the dataset is small.

The engines are still available in `predict.py --astro-engines` for research, shown
next to (never mixed into) the statistical prediction:
```bash
pip install pyswisseph   # Debian/Ubuntu system Python: install inside a venv
python predict.py soccer top5 examples/club_fixtures_astro.csv --astro-engines
```
Fixtures need `kickoff_utc` (ISO, UTC) and either `lat, lon` columns or a home club
listed in `venues.py`. Ephemeris files go in `../data/ephe` (or set `SE_EPHE_PATH`).

## On "≥ 70% accuracy"
Predicting *every* match at 70% is not achievable for 3-way soccer (bookmakers
reach about 53–55% in top leagues) or for the NHL (about 58–62%). It is roughly
achievable for the NBA (about 68–70%) and for ATP/WTA tennis when odds are used
(about 70–72%). What the tool does instead is **selective prediction**: it learns,
from past out-of-sample results only, the confidence level above which its picks
have historically been ≥ 70% right, and flags those matches `HIGH-CONFIDENCE`.
Accuracy alone does not mean profit: the betting market prices those same
favourites.

## Usage
```bash
bash ../scripts/fetch_data.sh      # once, from sportspredict/: downloads the datasets into ../data
pip install -r requirements.txt
python backtest.py nba                         # or intl | club | top5 (soccer also runs over/under)
python backtest.py club --ou-only              # over/under 2.5 only
python backtest.py my_tennis.csv tennis 2018   # your data: sport + first test year
python predict.py basketball nba examples/nba_fixtures.csv
python predict.py soccer intl examples/intl_fixtures.csv          # 1X2 + over/under 2.5
python predict.py soccer my_league.csv fixtures.csv --ou-line 3.5
python predict.py hockey my_nhl_history.csv my_fixtures.csv
python predict.py tennis atp_matches.csv fixtures.csv --esoteric
```
Canonical CSV columns: `date, home, away, home_score, away_score` and optionally
`neutral, friendly, surface, odds_home, odds_draw, odds_away, odds_over, odds_under,
home_birth, away_birth` (`league` is also used, to track each competition's scoring level).
Tennis also accepts Sackmann-style files (`winner_name, loser_name, tourney_date,
surface, winner_dob, loser_dob, odds_winner, odds_loser`); winner and loser are
randomised into P1/P2. Hockey: record the final winner including OT/shootout
(2-way). Historical datasets go in `../data` (download them with `bash scripts/fetch_data.sh` from the repository root, or set `SP_DATA`).
