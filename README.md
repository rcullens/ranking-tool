# Six-Man Rankings

Canonical source: **https://github.com/rcullens/ranking-tool**

A standalone Python toolkit that publishes **objective Texas UIL six-man high school football power rankings**, with a live Thu–Fri–Sat score pull so the list and comparison graph update as finals land.

The model is built for a league where Friday nights are high-scoring, mercy-rule endings are common, entire two-way lineups graduate in one May, and a 10–0 district champion may never have left its own county. Bundled synthetic fixtures — real program names, a fictional slate — let you run the pipeline without credentials. Point `SIXMAN_FEED_URL` at a JSON score feed (or `POST /api/ingest`) for a real Friday night.

## Install

Python 3.10+. The ranking engine is stdlib; the live graph needs FastAPI.

```bash
git clone https://github.com/rcullens/ranking-tool.git
cd ranking-tool
python -m venv .venv
source .venv/bin/activate
pip install -e ".[web,dev]"
cd web && npm install && npm run build && cd ..
```

Or, from `requirements.txt`:

```bash
pip install -e .
pip install -r requirements.txt
```

## Run

```bash
# Bundled West Texas / Panhandle / Trans-Pecos sample season
sixman-rank
python -m sixman_rankings

# Your weekly files
sixman-rank --teams teams.csv --games games.csv \
            --roster roster_factors.csv --panel panel_adjustments.csv \
            --priors priors.csv

# Directory of the standard filenames
sixman-rank --data-dir ./my-week --through-week 6 --format table

# Division split, recency, home field, exports
sixman-rank --classification DI
sixman-rank --split
sixman-rank --recency-half-life 4 --home-field 40
sixman-rank --out rankings.json --out-csv rankings.csv \
            --history-out history.json --history-csv history.csv

# What-if (does not write back to the season)
sixman-rank what-if --home borden-county --away sterling-city \
                    --home-score 54 --away-score 48
sixman-rank what-if --home marathon --away follett --margin 12 --neutral

# Live board (graph + table). Polls Thu/Fri/Sat automatically.
sixman-rank serve --host 127.0.0.1 --port 43127

# JSON snapshots for the Android APK (no phone-side Python)
sixman-rank export-offline --out web/public/offline

# Pull scores once (JSON feed and/or football-night replay)
sixman-rank sync --force
SIXMAN_FEED_URL=https://example.com/sixman-scores.json sixman-rank sync

# Sanity-check a season against expectation cards
sixman-rank validate
sixman-rank validate --data-dir ./my-week --expectations ./my-week/validation_expectations.json

# Machine-readable stdout
sixman-rank --format json
sixman-rank --format csv --top 10
sixman-rank --no-panel
sixman-rank --panel-mix 0.15
```

`rank` is an alias for `sixman-rank`. Bare flags still mean `sixman-rank rank …`.

See the repository working tree for the full Android APK, library, four-pillar model, week-to-week toolkit, live scores, input schema, and project layout documentation.
