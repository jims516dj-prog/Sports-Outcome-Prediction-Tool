#!/usr/bin/env bash
# Download the public datasets and ephemeris files used by sportspredict/ into ./data
# (about 35 MB). Run from the repository root:  bash scripts/fetch_data.sh
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/of data/ephe
get() { curl -fsL --retry 3 --max-time 120 -o "$2" "$1" || { rm -f "$2"; echo "  skipped: $1"; }; }
GH=https://raw.githubusercontent.com

echo "International results (martj42/international_results)"
get $GH/martj42/international_results/master/results.csv data/intl.csv

echo "NBA game log 1946-2015 (fivethirtyeight/data)"
get $GH/fivethirtyeight/data/master/nba-elo/nbaallelo.csv data/nba.csv

echo "Club seasons 2012-13..2019-20 without kickoff times (footballcsv)"
for s in 2012-13 2013-14 2014-15 2015-16 2016-17 2017-18 2018-19 2019-20; do
  for pair in england:eng.1 espana:es.1 deutschland:de.1; do
    repo=${pair%%:*}; lg=${pair##*:}
    get "$GH/footballcsv/$repo/master/2010s/$s/$lg.csv" "data/club_${lg}_$s.csv"
  done
done

echo "Top-five-league seasons 2010-11..2024-25 with kickoff times (openfootball/football.json; a few early Serie A / Ligue 1 seasons do not exist and are skipped)"
for s in 2010-11 2011-12 2012-13 2013-14 2014-15 2015-16 2016-17 2017-18 2018-19 2019-20 \
         2020-21 2021-22 2022-23 2023-24 2024-25; do
  for lg in en.1 de.1 es.1 it.1 fr.1; do
    get "$GH/openfootball/football.json/master/$s/$lg.json" "data/of/${s}_$lg.json"
  done
done

echo "Swiss Ephemeris files (planets, Moon, asteroids, fixed stars)"
for f in sepl_18.se1 semo_18.se1 seas_18.se1 sefstars.txt; do
  get "$GH/aloistr/swisseph/master/ephe/$f" "data/ephe/$f"
done
echo "done: $(find data -type f | wc -l) files in data/"
