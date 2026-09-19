"""Recursive three-tier strength of schedule.

Tier 0 is a team's own capped-margin efficiency (and win rate).
Tier 1 averages direct opponents' records and efficiency.
Tier 2 averages opponents' opponents' collective efficiency.

A damped recursion of depth 3 walks those hops so a win over a team that
feasted on cupcakes is not treated the same as a win over a team that
survived a connected West Texas slate.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Iterable, Mapping, Sequence

from sixman_rankings.margin import signed_capped_margin
from sixman_rankings.models import EngineConfig, Game
from sixman_rankings.recency import lookup_weight, resolve_as_of_week, weights_by_game


def played_opponents(games: Iterable[Game]) -> dict[str, list[str]]:
    """Adjacency list from *final* games only."""

    opps: dict[str, list[str]] = defaultdict(list)
    for game in games:
        if not game.is_final:
            continue
        opps[game.home_id].append(game.away_id)
        opps[game.away_id].append(game.home_id)
    return dict(opps)


def _weighted_mean(pairs: Sequence[tuple[float, float]]) -> float:
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return 0.0
    return sum(value * w for value, w in pairs) / total_w


def team_efficiency(
    games: Iterable[Game],
    mercy_cap: int,
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Mean capped point differential per team (0.0 if they have no finals).

    When ``weights`` is provided (recency), each final is a weighted observation.
    """

    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for game in games:
        if not game.is_final:
            continue
        assert game.home_score is not None and game.away_score is not None
        w = lookup_weight(game, weights)
        buckets[game.home_id].append(
            (signed_capped_margin(game.home_score, game.away_score, mercy_cap), w)
        )
        buckets[game.away_id].append(
            (signed_capped_margin(game.away_score, game.home_score, mercy_cap), w)
        )
    return {team: _weighted_mean(vals) for team, vals in buckets.items()}


def team_win_pct(
    games: Iterable[Game],
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Win percentage with ties as a half-win. Missing teams are omitted."""

    wins: dict[str, float] = defaultdict(float)
    played: dict[str, float] = defaultdict(float)
    for game in games:
        if not game.is_final:
            continue
        assert game.home_score is not None and game.away_score is not None
        w = lookup_weight(game, weights)
        played[game.home_id] += w
        played[game.away_id] += w
        if game.home_score > game.away_score:
            wins[game.home_id] += w
        elif game.away_score > game.home_score:
            wins[game.away_id] += w
        else:
            wins[game.home_id] += 0.5 * w
            wins[game.away_id] += 0.5 * w
    return {team: wins[team] / played[team] for team in played if played[team] > 0}


def _mean_or_zero(values: Sequence[float]) -> float:
    return fmean(values) if values else 0.0


def recursive_quality(
    efficiency: Mapping[str, float],
    opponents: Mapping[str, Sequence[str]],
    *,
    depth: int,
    alpha: float,
    team_ids: Sequence[str],
) -> dict[str, float]:
    """Damped recursion: ``Q_k = (1-α) * own + α * mean(Q_{k-1} of opponents)``.

    ``depth=3`` is the required three-tier walk. Teams with no opponents
    keep their own efficiency at every hop.
    """

    own = {tid: float(efficiency.get(tid, 0.0)) for tid in team_ids}
    quality = dict(own)
    hops = max(0, depth)
    for _ in range(hops):
        nxt: dict[str, float] = {}
        for tid in team_ids:
            opps = opponents.get(tid, ())
            if not opps:
                nxt[tid] = quality[tid]
                continue
            # Pure opponent walk: after k hops this is the mean efficiency of
            # the k-hop neighborhood. ``alpha`` damps toward the previous hop
            # (not toward own margin) so a 45-point cupcake diet cannot keep
            # leaking into SOS.
            opp_q = _mean_or_zero([quality.get(o, 0.0) for o in opps])
            nxt[tid] = (1.0 - alpha) * quality[tid] + alpha * opp_q
        quality = nxt
    return quality


def opponent_tier_efficiency(
    team_id: str,
    efficiency: Mapping[str, float],
    opponents: Mapping[str, Sequence[str]],
) -> float:
    """Tier 1: mean efficiency of direct opponents."""

    opps = opponents.get(team_id, ())
    if not opps:
        return 0.0
    return _mean_or_zero([efficiency.get(o, 0.0) for o in opps])


def opponent_tier_win_pct(
    team_id: str,
    win_pct: Mapping[str, float],
    opponents: Mapping[str, Sequence[str]],
) -> float:
    """Tier 1 records: mean win percentage of direct opponents."""

    opps = opponents.get(team_id, ())
    if not opps:
        return 0.5
    return _mean_or_zero([win_pct.get(o, 0.5) for o in opps])


def opp_opp_efficiency(
    team_id: str,
    efficiency: Mapping[str, float],
    opponents: Mapping[str, Sequence[str]],
) -> float:
    """Tier 2: collective efficiency of opponents' opponents (self excluded)."""

    values: list[float] = []
    for opp in opponents.get(team_id, ()):
        for hop2 in opponents.get(opp, ()):
            if hop2 == team_id:
                continue
            values.append(efficiency.get(hop2, 0.0))
    return _mean_or_zero(values)


def strength_of_schedule(
    team_ids: Sequence[str],
    games: Sequence[Game],
    config: EngineConfig,
    *,
    as_of_week: int | None = None,
) -> dict[str, float]:
    """Combined SOS in capped-PD units, before the geographic density haircut.

    ``sos = w1 * (opp efficiency blended with opp win%) + w2 * opp-opp efficiency``
    plus a recursive quality walk so the three tiers share one consistent
    evaluation rather than three disconnected averages. Leaf efficiency and
    win% are recency-weighted when ``config.recency_half_life > 0``.
    """

    finals = [g for g in games if g.is_final]
    week = resolve_as_of_week(finals, as_of_week)
    weights = weights_by_game(finals, week, config.recency_half_life)
    opps = played_opponents(finals)
    eff = team_efficiency(finals, config.mercy_cap, weights)
    win_pct = team_win_pct(finals, weights)
    quality = recursive_quality(
        eff,
        opps,
        depth=config.sos_depth,
        alpha=config.sos_alpha,
        team_ids=team_ids,
    )

    # Win% is mapped onto the same capped-PD scale as efficiency so the
    # two opponent signals can be averaged without a unit mismatch.
    # 1.000 win% → +mercy_cap, .000 → -mercy_cap, .500 → 0.
    def winpct_as_pd(pct: float) -> float:
        return (2.0 * pct - 1.0) * config.mercy_cap

    out: dict[str, float] = {}
    for tid in team_ids:
        opp_eff = opponent_tier_efficiency(tid, eff, opps)
        opp_rec = winpct_as_pd(opponent_tier_win_pct(tid, win_pct, opps))
        # Direct-opponent term: efficiency and records, then nudged by the
        # recursive quality so a 3-0 cupcake diet cannot hide behind raw PD.
        direct = 0.5 * opp_eff + 0.3 * opp_rec + 0.2 * quality.get(tid, 0.0)
        hop2 = opp_opp_efficiency(tid, eff, opps)
        out[tid] = (
            config.sos_opponent_weight * direct
            + config.sos_opp_opp_weight * hop2
        )
    return out
