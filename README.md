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

## Phone-only (Pixel / Chrome, no PC)

The Vite board in `web/` is a static site. **Statewide / Districts / Regions, charts, presets, and tabs work from the bundled `public/offline` snapshots** — no local Python server. What-if, ingest, and live Thu–Sat sync need a remote API URL when you add one later.

**Phone HTTPS (GitHub Pages, no Vercel):** open **https://rcullens.github.io/ranking-tool/** in **Chrome on the Pixel 9 Pro**:

1. Chrome menu (⋮) → **Install app** / **Add to Home screen**.
2. Open **Six-Man** from the home screen. Boards and charts load from the bundled `offline/*.json` snapshot.
3. Leave **Phone / APK → Live server URL** blank unless you have a public `sixman-rank serve` API.

Every push to `main` rebuilds `web/` with `VITE_BASE=/ranking-tool/` and publishes the `gh-pages` branch (workflow `.github/workflows/pages.yml`). The build does **not** run Python or `export-offline`. The JSON under `web/public/offline/` must already be in git (`npm run prebuild` fails if they are missing).

```bash
# refresh snapshots before a release (on a machine with Python)
sixman-rank export-offline --out web/public/offline
git add web/public/offline && git commit && git push origin main
```

## Install and run as an Android APK

This is a **browser GUI** (React). There is no Play Store listing. An APK is a Capacitor wrapper around **that same full GUI** — not a lite phone skin. Charts, Statewide / Districts / Regions, presets, classification splits, what-if, ingest, and every ranking column stay on the phone. The APK also ships a bundled ranking snapshot so it opens with no server. Point it at `sixman-rank serve` when you want live Thursday–Saturday sync.

### Fastest phone install (no APK file)

1. On the Pixel, open **https://rcullens.github.io/ranking-tool/** in **Chrome**.
2. Chrome menu → **Install app** / **Add to Home screen**.
3. Launch it from the home-screen icon. It runs fullscreen like a native app.

### Build a sideload APK (Android Studio)

You need [Android Studio](https://developer.android.com/studio) (Android SDK 35) on a Mac, Windows, or Linux machine. Work from a clone of https://github.com/rcullens/ranking-tool.

```bash
git clone https://github.com/rcullens/ranking-tool.git
cd ranking-tool
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[web]"
./scripts/bootstrap-android.sh     # icons, wrapper jar, offline JSON, npm, cap sync
```

**Android Studio path**

```bash
cd web
npx cap open android
```

1. Wait for Gradle sync to finish.
2. **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
3. Click **locate**. Debug APK:

`web/android/app/build/outputs/apk/debug/app-debug.apk`

**CLI path** (Android SDK 35, `ANDROID_HOME` or `ANDROID_SDK_ROOT` set):

```bash
./scripts/build-apk.sh
# same artifact: web/android/app/build/outputs/apk/debug/app-debug.apk
```

The wrapped app is **Six-Man Rankings** (`com.sixman.rankings`), version **0.3.0** (same as the Python package and the Vite board). The web server stays first-class: use `sixman-rank serve` on a computer for live Thu–Sat sync. The APK is that same board plus a bundled snapshot.

### GitHub Release APK (phone download, no PC)

Tag **v0.3.0** on https://github.com/rcullens/ranking-tool/releases. Attach `app-debug.apk` from a machine that has Android Studio (this cloud image has no Android SDK, so it cannot compile the APK).

On the Pixel, with no USB cable:

1. Chrome → the Release page → download `app-debug.apk`.
2. Settings → **Install unknown apps** → allow **Chrome**.
3. Tap the download → **Install** → **Open** Six-Man Rankings.

### Put the APK on a phone (if you already have the file)

1. Open `app-debug.apk` from Chrome Downloads, Drive, or Messages.
2. Settings → **Install unknown apps** → allow the app you used to open the file (Files, Chrome, Drive).
3. Tap the APK → **Install** → **Open**. Installing over an older Six-Man Rankings build is the normal **Update** / install-over prompt.
4. In-app: **Phone / APK** repeats these notes and accepts a live-server URL.

The icon is **Six-Man Rankings**. Leave the live URL blank to stay on the snapshot inside the APK.

### Live scores from the phone

The APK cannot run the Python engine. For Friday-night updates:

1. On a computer on the same Wi-Fi: `sixman-rank serve --host 0.0.0.0 --port 43127`
2. Allow the port through the computer firewall.
3. Find the computer’s LAN address (`ipconfig` / `ip addr`, e.g. `192.168.1.20`).
4. In the phone app: **Phone / APK** → Live server URL → `http://192.168.1.20:43127` → Save.

Leave the URL blank to stay on the bundled snapshot.

### Refresh the snapshot inside the APK

```bash
sixman-rank export-offline --out web/public/offline
cd web && npm run android:sync
```

Then rebuild the APK. Play Store / signed release: Android Studio → **Generate Signed Bundle / APK** with your own keystore. This repo does not ship a store listing.

### Library

```python
from sixman_rankings import RankingEngine, rank_season
from sixman_rankings.io import load_sample_dataset

teams, games, roster, panel, priors = load_sample_dataset()
table = rank_season(teams, games, roster=roster, panel=panel, priors=priors)

engine = RankingEngine(teams, games, roster=roster, panel=panel, priors=priors)
week_4 = engine.process_through_week(4)
week_5 = engine.process_through_week(5)
```

`process_through_week` always rebuilds from the preseason prior, so you can jump to any Friday without replaying by hand. `engine.weekly_history(9)` returns every week from preseason through Week 9 with rank/power deltas attached.

```python
from sixman_rankings import simulate_what_if
from sixman_rankings.export import write_rankings_json

report = simulate_what_if(teams, games, home_id="borden-county", away_id="rankin", margin=21)
write_rankings_json("week9.json", table, week=9, history=engine.weekly_history(9))
```

## The four pillars

### 1. Modified point differential (capped at 45)

UIL six-man ends a game when one team leads by **45 or more** at halftime or at any point in the second half. In the vernacular the loser was *45'ed*.

Every margin that enters Elo, SOS, or the published CapPD column is clamped to `[-45, +45]`. A 72–12 and a 52–7 are the same dominance event. Running it up past the mercy rule cannot inflate a rating.

### 2. Recursive multi-tier strength of schedule

Simple opponent win percentage is a bad SOS in six-man: an isolated district can go 10–0 against itself. The engine walks **three tiers**:

| Tier | What it measures |
| --- | --- |
| 0 | A team's own mean capped point differential and win rate |
| 1 | Direct opponents' records and efficiency |
| 2 | Opponents' opponents' collective efficiency |

A damped recursion of depth 3 (`Qₖ = (1−α)·own + α·mean(Qₖ₋₁ of opponents)`) keeps those hops on one scale. The published SOS is then:

```
SOS = 0.65 · (blend of opponent efficiency, opponent win%, recursive quality)
    + 0.35 · (opponents' opponents' efficiency)
```

**Geographic density coefficient.** After SOS is computed, it is multiplied by a coefficient in `[0.72, 1.00]` that penalizes districts whose entire non-district window does not overlap the rest of the state. Three signals:

1. Overlap between this district's non-district opponents and every other district's non-district opponents. Zero overlap is the classic rural bubble.
2. How many distinct regions a team's opponents represent.
3. How many regions those opponents themselves reach (two hops).

A closed Trans-Pecos loop that only plays itself sits at the floor. A West Texas slate that crosses Rolling Plains and the Panhandle stays near `1.00`. Isolated teams also keep a slightly smaller share of their Elo deviation from the league mean, so intra-bubble rating transfers cannot buy a statewide #1.

### 3. Dynamic margin-capped Elo ("The Toy")

Rating points move from the **expected scoring spread**, not from a binary W/L.

1. Elo win probability `E` (400-point logistic, 35-point home-field edge).
2. Expected spread `μ = 45 · (2E − 1)` using a tighter 280-point scale — a 300-point favorite is expected to nearly 45 the opponent, so another mercy-rule win against a cupcake barely moves the market.
3. Residual `r = capped_actual − μ`.
4. Cover multiplier `1 + λ · log(1+|r|) / log(1+45)`, `λ = 0.55`. The first points above the number are worth more than the last; everything saturates at the mercy cap.
5. Asymmetric K: when the favorite fails to cover or the underdog covers, K is boosted 15%. The exchange itself stays zero-sum.

```
Δ = K_eff · multiplier · (r / 45)
home += Δ
away -= Δ
```

Beating a 20-point spread by 10 moves the market. Beating a 40-point spread by 2 barely does. That is how scheduling bias is removed *inside* the game-by-game engine, before SOS ever touches the table.

### 4. Roster-turnover decay and hybrid panel ("one-hit wonder" filter)

Small-school six-man can graduate an entire two-way lineup. Last November's 1760 is a rumor until the new QB takes a snap.

**Automated decay.** Combined turnover is `0.4 · graduation_rate + 0.6 · positional_turnover` (both in `[0, 1]`). Below 0.45 (ordinary senior-class replacement) nothing is stripped. At or above 0.90 (near-total positional wipeout) the engine strips **35%** of the prior's deviation from the league mean:

```
preseason = 1500 + (legacy − 1500) · (1 − 0.35)
```

A 1800 prior becomes 1695. The program keeps an identity; it does not open the year as an automatic top-two side.

**Human panel.** Optional rows modeled after Dave Campbell's Texas Football (or any coaches' poll) live on the same 1500-centered scale. At 0 games the published power is

```
(1 − w) · computer + w · panel_rating
```

with default `w = 0.25 · row_weight`. The mix halves every 3.5 games played so the magazine vote hands the season to the computer. Pair the panel with turnover decay when you already know the two-way star class is gone — do not leave a stale 1725 on a gutted roster and wait for October.

## Week-to-week toolkit

These sit on top of the four pillars. They do not replace the 45-point cap, the 3-tier SOS, The Toy, or the 35% turnover strip.

### 1. Recency weighting

When ranking through week *W*, a final from week *w* is weighted

```
0.5 ** ((W − w) / half_life)
```

Default half-life is **5 weeks** (`EngineConfig.recency_half_life` / `--recency-half-life`). The weight scales both The Toy's rating exchange and the leaf efficiency / win% that feed SOS. `--recency-half-life 0` turns decay off.

### 2. Rating confidence / uncertainty

Each team gets `σ = 120 / sqrt(games + 2)`, then widened when geographic density is low. The published **Conf** column is `1 − σ/120`. A row is flagged **low confidence** (trailing `*` on the rank, plus a note) when it has fewer than 3 games or Conf &lt; 0.40. Early-season and isolated slates stay visibly uncertain until the sample grows.

### 3. Classification / division awareness

`teams.classification` holds tags such as `1A DI` and `1A DII`. `--classification DI` (or `DII`, `1A Division II`, `d2`) publishes a within-class table. `--split` prints both divisions. Bare `DI` does **not** match `DII`.

### 4. Week-over-week movement

`RankingEngine.weekly_history` stores every week from 0 (preseason) onward. The table's **Mv** column is `previous_rank − current_rank` (positive = rose). Notable movers print under the table. `--no-movement` skips deltas.

### 5. Export

Stable schema version **1.1** (`sixman_rankings.export.RANKING_FIELDS`). `--out` / `--out-csv` write the current table; `--history-out` / `--history-csv` add one snapshot per week. Same columns go to stdout `--format json|csv`. Downstream sheets (Sixmanmadness-style) can depend on the key set; new fields are appended, never renamed.

### 6. What-if simulator

`sixman-rank what-if --home X --away Y --home-score A --away-score B` (or `--margin`, mercy-capped at 45) rebuilds on a **copy** of the game list. The caller's season files and in-memory `games` list are not appended to. The report shows provisional rank/power deltas for the two clubs and anyone else who moved.

### 7. Home / neutral site factor

The Toy adds `home_field` Elo points (default **35**) to the home side before the expected spread is computed. `games.neutral=true` or `what-if --neutral` zeroes it. `--home-field 0` disables the edge for a whole run.

### 8. Tie handling

Published order, and only the published order:

1. **Power** (the blended rating)
2. **SOS** (density-adjusted)
3. **Head-to-head** season series among the tied pair
4. **Capped point differential**
5. `team_id` (deterministic leftover)

H2H cycles fall through to CapPD. This sort does not feed back into Elo or SOS.

### 9. Dual view (power + district W-L)

The **Dist** column and the district standings block are simple district W-L from `district_game=true` rows. They are **not** mixed into Power. `--top` still lists every district member in the standings block. `--no-district` hides the block.

`--district "8-1A DI"` and `--region west-texas` republish a **local** power table (ranks restart at 1). `--split-district` and `--split-region` print one table per group. The live board has the same three views: Statewide, Districts, Regions.

### 10. Validation harness

`sixman-rank validate` (or `python -m sixman_rankings.validate`) scores structural checks (contiguous ranks, CapPD bound, district W-L vs flags, confidence-flag consistency) plus JSON expectation cards. The bundled sample ships `sixman_rankings/data/validation_expectations.json`. No live scrape.

```json
{"type": "top_n", "team_id": "borden-county", "n": 3}
{"type": "not_rank", "team_id": "marathon", "rank": 1}
{"type": "note_contains", "team_id": "rankin", "text": "one-hit-wonder"}
```

Supported card types: `top_n`, `min_rank`, `not_rank`, `record`, `density_below`, `note_contains`, `turnover_at_least`.

## Live scores and the comparison graph

UIL does not publish a machine-readable statewide 6-man feed, and [sixmanfootball.com](https://sixmanfootball.com) (the community scoreboard) sits behind Cloudflare with no public API. The live layer is therefore a **puller + webhook + football-night scheduler**, not a pretend UIL scrape.

### What runs on Thursday, Friday, and Saturday

`sixman-rank serve` starts FastAPI on port 43127 and a background poller (America/Chicago):

- **Thu / Fri / Sat 10:00–23:59**, plus Sunday before 2am for late Saturday games
- Interval: 20 seconds inside the window, 2 minutes off-window (`SIXMAN_SYNC_INTERVAL_SEC` overrides)
- Each tick: pull `SIXMAN_FEED_URL` if set, merge finals, republish rankings
- **Sync scores now** in the UI (or `sixman-rank sync --force`) does the same immediately

When every game in the current week is final, the status line flips to **Week N published**.

### How to feed real scores

JSON body (file, HTTP feed, or `POST /api/ingest`):

```json
{
  "games": [
    {
      "week": 5,
      "date": "2026-09-18",
      "home": "Borden County",
      "away": "Garden City",
      "home_score": 54,
      "away_score": 36,
      "status": "final"
    }
  ]
}
```

Team names are resolved onto slugs (`Borden County` → `borden-county`). Example file: `sixman_rankings/data/live_feed.example.json`.

```bash
export SIXMAN_FEED_URL=https://your-host/sixman-scores.json
sixman-rank serve
curl -X POST http://127.0.0.1:43127/api/ingest -H 'Content-Type: application/json' -d @scores.json
```

If no feed URL is set, the bundled season starts through **Week 4** and the poller **replays held Friday finals** two at a time during the football window so the graph actually moves. That is a demo stand-in, not a claim that UIL was scraped.

### Comparison graph

Open the served app. The chart is a multi-series line (power or inverted rank vs week), same idea as a spreadsheet compare:

- **Last week's Top 10** / **This week's Top 10** / **Undefeated** / **DI** / **DII** / any district / any region
- Checkbox any mix of programs
- Click a table name to add or drop that line
- **Statewide / Districts / Regions** tabs: local power rank plus district W-L race (Dist is context only)
- The page polls so new finals redraw the lines without a refresh

API used by the page: `/api/status`, `/api/sync`, `/api/compare?teams=a,b&metric=power`, `/api/rankings`, `/api/boards`, `/api/presets`.

## Config knobs

All live on `EngineConfig`. CLI flags cover the ones you change week to week.

| knob | default | CLI | role |
| --- | --- | --- | --- |
| `mercy_cap` | 45 | | UIL mercy-rule cap |
| `home_field` | 35 | `--home-field` | Toy expected-spread HFA (Elo points) |
| `recency_half_life` | 5 | `--recency-half-life` | weeks to half-weight a game; `0` disables |
| `panel_mix` | 0.25 | `--panel-mix` / `--no-panel` | preseason magazine blend |
| `confidence_base_sigma` | 120 | | uncertainty at the prior |
| `confidence_min_games` | 3 | | low-confidence floor |
| `confidence_flag` | 0.40 | | Conf below this is flagged |
| `elo_k` / `cover_lambda` / `upset_boost` | 28 / 0.55 / 0.15 | | Toy update |
| `sos_depth` / `sos_to_elo` | 3 / 12 | | recursive SOS |
| `turnover_strip` | 0.35 | | one-hit-wonder haircut |
| `density_floor` | 0.72 | | insular SOS floor |

## Input schema

All IDs are stable slugs (`borden-county`). Files may be `.csv` or `.json` (a list, or an object with a `teams` / `games` / `roster` / `panel` / `priors` key).

### `teams.csv`

| column | required | notes |
| --- | --- | --- |
| `team_id` | yes | slug |
| `name` | yes | display name |
| `district` | yes | e.g. `8-1A DI` — density groups on this string |
| `region` | yes | e.g. `west-texas`, `panhandle`, `trans-pecos` |
| `classification` | no | `1A DI` / `1A DII` (or any tag `--classification` can match) |
| `city` | no | |
| `lat`, `lon` | no | reserved for future distance work; unused by density |

### `games.csv`

| column | required | notes |
| --- | --- | --- |
| `game_id` | yes | unique |
| `week` | yes | integer, used for `--through-week` |
| `date` | yes | ISO date; sort key |
| `home_id`, `away_id` | yes | must exist in teams |
| `home_score`, `away_score` | no | blank = scheduled, not final |
| `district_game` | no | `true` / `false` — feeds the Dist column only |
| `neutral` | no | strips the home-field Elo edge |

Leave scores blank for future Fridays. Density still sees the scheduled opponent; Elo and SOS wait for a final.

### `roster_factors.csv` (optional)

| column | notes |
| --- | --- |
| `team_id`, `season` | |
| `graduation_rate` | 0–1 share of the senior class that left |
| `positional_turnover` | 0–1 share of starting spots (QB, skill, line, DB) that must be replaced |
| `notes` | free text |

### `panel_adjustments.csv` (optional)

| column | notes |
| --- | --- |
| `team_id`, `season` | |
| `panel_rating` | Elo-scale prior (league mean ≈ 1500) |
| `weight` | 0–1 multiplier on the engine's panel mix |
| `notes` | e.g. "DCTF preseason #2" |

### `priors.csv` (optional)

| column | notes |
| --- | --- |
| `team_id`, `season` | |
| `rating` | previous computer rating; turnover decay is applied to this |

`--season` keeps only matching roster / panel / prior rows.

Sample files live in [`sixman_rankings/data/`](sixman_rankings/data/).

## What the sample season is supposed to show

Twenty real-named programs, four regions, nine weeks:

- **Borden County, Sterling City, Follett** all finish 8–1 on connected slates that cross West Texas, the Rolling Plains, and the Panhandle. They should occupy the top of the table. Follett beat Sterling; Sterling beat Borden; Borden crushed Jayton, who beat Follett — a cycle the Toy engine and 3-tier SOS have to untangle from *margins*, not from W/L.
- **Marathon** is 9–0 and 45'ed the Trans-Pecos loop every week. No non-district opponent is shared with the rest of the state. Density sits near the floor; Marathon must **not** publish as #1.
- **Rankin** is last year's 12–1 one-hit wonder (`prior = 1765`, graduation 0.90, positional turnover 0.95). The 35% strip lands before week 1. The panel still has them at 1725; that vote fades as the 3–6 tape accumulates.

## Example output

```
Texas UIL Six-Man Power Rankings  ·  through Week 9
Cap 45  ·  Toy Elo  ·  3-tier SOS  ·  recency  ·  * = low confidence

Rk  Mv  Team           Rec  Dist  Cls       Power      ±  Conf     SOS  Dens  Notes
 1   —  Borden County  8-1  3-0   1A DI    1628.9   36.5  0.70   -1.10  0.97
 2   —  Sterling City  8-1  3-0   1A DI    1597.8   36.5  0.70   -0.63  0.97
 3   —  Rankin         3-6  1-2   1A DI    1571.7   36.5  0.70    3.99  0.97  one-hit-wonder decay
 4   —  Follett        8-1  3-0   1A DII   1560.7   36.3  0.70   -4.55  0.99
...
 9   —  Marathon       9-0  6-0   1A DII   1524.3   39.6  0.67   -9.33  0.73  insular schedule
```

The *shape* is the point of the fixture: connected 8–1s on top, Marathon's isolated 9–0 held mid-table (wider `±` because density is low), Rankin decayed off a 1765 prior and carrying the league's best SOS.

Columns:

| column | meaning |
| --- | --- |
| Mv | Rank change vs last week (`+` rose) |
| Rec / Dist | Overall W-L and district W-L (Dist is context only) |
| Cls | Classification tag |
| Power | Final published rating |
| ± / Conf | One-sigma band and 0–1 confidence |
| SOS | Three-tier schedule score, already × density |
| Dens | Geographic density coefficient |

## Tests

```bash
pytest
```

Coverage that the architecture requires:

- 45-point cap (blowouts collapse to one dominance weight)
- Toy Elo expected-spread updates, zero-sum exchange, logarithmic cover multiplier, asymmetric K, home-field tilt
- SOS recursion (direct opponents + opponents' opponents; cupcake slates rank below connected slates)
- 35% near-total turnover decay
- Recency: a Week 9 mirror of a Week 1 45 moves Elo more than the August copy
- Confidence shrinks from Week 1 (all flagged) to Week 9
- What-if is non-destructive and moves the provisional table
- Export schema 1.1 key set; H2H beats CapPD when Power and SOS tie
- Sample-season pipeline + `validate` expectation cards

## Project layout

```
sixman_rankings/
  constants.py     knobs (mercy cap, K, SOS, recency, confidence)
  models.py        Team, Game, RosterFactor, PanelAdjustment, EngineConfig
  margin.py        45-point cap
  elo.py           The Toy engine (incl. home-field)
  sos.py           3-tier recursive SOS (recency-weighted leaves)
  recency.py       week half-life weights
  confidence.py    sigma / low-confidence flag
  classify.py      DI / DII matching
  ties.py          power → SOS → H2H → CapPD
  geography.py     density coefficient
  turnover.py      one-hit-wonder filter
  panel.py         DCTF-style blend
  history.py       rank/power deltas, district and region groups
  export.py        schema 1.1 CSV/JSON
  whatif.py        non-destructive simulator
  validate.py      expectation-card harness
  pipeline.py      week-over-week RankingEngine
  io.py            CSV / JSON loaders
  live/            JSON feed, webhook, Thu–Sat window, replay
  web/app.py       FastAPI live board
  cli.py           sixman-rank {rank, what-if, validate, sync, serve, export-offline}
  offline.py       JSON snapshots for the Android/PWA shell
web/               React GUI (Vite + Recharts + Capacitor Android)
  public/offline   bundled rankings the APK opens with
  android/         native project — npm run android:sync then assembleDebug
  data/            synthetic 2025 fixtures + validation cards
tests/
```

Override any knob by passing a custom `EngineConfig` into `rank_season` / `RankingEngine`.
