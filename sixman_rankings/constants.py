"""Tunable constants for the six-man ranking pipeline.

The defaults are calibrated for Texas UIL six-man football: high scoring,
frequent mercy-rule endings, small-school roster churn, and regionally
clustered schedules. Override via :class:`sixman_rankings.models.EngineConfig`.
"""

from __future__ import annotations

# UIL six-man mercy rule: the game ends when a team leads by 45 or more
# at halftime or at any point in the second half. In six-man slang the
# loser was "45'ed." Margins at or above this cap share one dominance weight.
MERCY_CAP = 45

# Classic Elo scale. A 400-point gap implies a 10:1 expected win ratio.
ELO_SCALE = 400.0
# Tighter scale used only when mapping Elo onto an expected point spread.
# A 300-point favorite is then expected to nearly 45 the opponent, so
# another mercy-rule win against a cupcake barely moves the market.
SPREAD_SCALE = 280.0
INITIAL_RATING = 1500.0

# K controls how many rating points move after one game. Six-man weeks are
# volatile, so this sits a bit above typical college-football K values.
ELO_K = 28.0

# Rural six-man home-field edge is real (travel, wind, field condition)
# but smaller than 11-man Friday-night crowds. Expressed in Elo points.
HOME_FIELD_ADVANTAGE = 35.0

# Extra cover-multiplier growth. At a 45-point residual the multiplier is
# 1 + COVER_LAMBDA; at a 0 residual it is 1.0. Logarithmic in between.
COVER_LAMBDA = 0.55

# Extra K applied when the underdog covers or the favorite fails to cover.
# Makes the engine asymmetric: upsets move the market more than expected wins.
UPSET_BOOST = 0.15

# Recursive SOS: three evaluation hops (own → opponents → opponents' opponents).
SOS_DEPTH = 3
# Mixing weight on the new opponent-neighborhood mean vs. the previous hop.
# 1.0 is a pure k-hop walk (required so own blowout margins do not leak into SOS).
SOS_ALPHA = 1.0
# How the two explicit SOS tiers combine after recursion.
SOS_OPPONENT_WEIGHT = 0.65
SOS_OPP_OPP_WEIGHT = 0.35
# Maps a +1 capped-PD SOS unit onto the Elo scale for the hybrid power score.
SOS_TO_ELO = 12.0

# Final computer blend before the human panel is mixed in.
ELO_BLEND = 0.66
SOS_BLEND = 0.34

# Near-total positional turnover strips this fraction of a team's deviation
# from the league mean (the "one-hit wonder" filter).
TURNOVER_STRIP = 0.35
# Turnover below this combined rate is treated as ordinary class replacement.
TURNOVER_FLOOR = 0.45
# Combined rate at which the full 35% strip is applied.
TURNOVER_FULL = 0.90

# Geographic density coefficient range. Fully insular districts sit at the floor.
DENSITY_FLOOR = 0.72
# At the density floor, keep this fraction of Elo deviation from the mean.
# A 9-0 bubble champion cannot ride intra-district transfers to #1 statewide.
DENSITY_ELO_FLOOR = 0.55

# Preseason panel mix at 0 games; decays exponentially with games played.
DEFAULT_PANEL_MIX = 0.25
PANEL_HALF_LIFE_GAMES = 3.5

# Minimum scheduled games before density is trusted; below this, density = 1.
DENSITY_MIN_SCHEDULED = 3

# Recency: a game's Elo/SOS weight halves every N weeks of age.
# Set to 0 to disable (every final counts equally, aside from sequential Elo).
RECENCY_HALF_LIFE_WEEKS = 5.0

# Confidence / uncertainty. sigma = BASE / sqrt(games + PRIOR), then inflated
# when the geographic density coefficient is low.
CONFIDENCE_PRIOR_GAMES = 2.0
CONFIDENCE_BASE_SIGMA = 120.0
CONFIDENCE_DENSITY_PENALTY = 0.35
CONFIDENCE_MIN_GAMES = 3
CONFIDENCE_FLAG = 0.40

# Tie-break epsilons. Power and SOS must be this close before H2H / CapPD fire.
TIE_POWER_EPS = 1e-6
TIE_SOS_EPS = 1e-6

# Stable export schema for sheets / Sixmanmadness-style downstream jobs.
EXPORT_SCHEMA_VERSION = "1.1"
