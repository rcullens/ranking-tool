"""Validation harness: score a season against known-outcome cards.

No live scrape. Point this at the bundled sample, or at your own
``validation_expectations.json`` next to a data directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

from sixman_rankings.io import DEMO_DATA, load_dataset, load_sample_dataset
from sixman_rankings.models import EngineConfig, Game, RankedTeam, Team


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


@dataclass
class ValidationReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(CheckResult(name, ok, detail))

    def summary(self) -> str:
        passed = sum(1 for c in self.checks if c.ok)
        lines = [f"Validation  ·  {passed}/{len(self.checks)} checks passed"]
        for check in self.checks:
            mark = "ok" if check.ok else "FAIL"
            lines.append(f"  [{mark}] {check.name}: {check.detail}")
        return "\n".join(lines)


def _by_id(rows: Sequence[RankedTeam]) -> dict[str, RankedTeam]:
    return {r.team_id: r for r in rows}


def _eval_expectation(exp: dict[str, Any], table: Sequence[RankedTeam]) -> CheckResult:
    kind = exp.get("type", "")
    tid = exp.get("team_id", "")
    row = _by_id(table).get(tid)
    name = f"{kind}:{tid}" if tid else kind
    if row is None and tid:
        return CheckResult(name, False, f"{tid} missing from table")

    if kind == "top_n":
        n = int(exp["n"])
        ok = row.rank <= n
        return CheckResult(name, ok, f"rank {row.rank} (need <= {n})")
    if kind == "min_rank":
        n = int(exp["n"])
        ok = row.rank >= n
        return CheckResult(name, ok, f"rank {row.rank} (need >= {n})")
    if kind == "not_rank":
        banned = int(exp["rank"])
        ok = row.rank != banned
        return CheckResult(name, ok, f"rank {row.rank} (must not be {banned})")
    if kind == "record":
        want = str(exp["record"])
        ok = row.record == want
        return CheckResult(name, ok, f"{row.record} vs {want}")
    if kind == "density_below":
        value = float(exp["value"])
        ok = row.density < value
        return CheckResult(name, ok, f"density {row.density:.3f} < {value}")
    if kind == "note_contains":
        text = str(exp["text"])
        ok = text.lower() in row.notes.lower()
        return CheckResult(name, ok, f"notes={row.notes!r}")
    if kind == "turnover_at_least":
        value = float(exp["value"])
        ok = row.turnover_decay + 1e-12 >= value
        return CheckResult(name, ok, f"turnover {row.turnover_decay:.3f} >= {value}")
    return CheckResult(name, False, f"unknown expectation type {kind!r}")


def structural_checks(
    teams: Sequence[Team],
    games: Sequence[Game],
    table: Sequence[RankedTeam],
    config: EngineConfig,
) -> list[CheckResult]:
    out: list[CheckResult] = []
    ranks = [r.rank for r in table]
    out.append(CheckResult(
        "contiguous_ranks",
        ranks == list(range(1, len(table) + 1)),
        f"ranks={ranks[:5]}…",
    ))
    ids = [r.team_id for r in table]
    out.append(CheckResult("unique_teams", len(ids) == len(set(ids)) == len(teams), f"{len(ids)} rows"))

    overflow = False
    for game in games:
        if not game.is_final:
            continue
        assert game.home_score is not None and game.away_score is not None
        if abs(game.home_score - game.away_score) > config.mercy_cap:
            overflow = True
            break
    bounded = all(abs(r.capped_pd) <= r.games_played * config.mercy_cap + 1e-6 for r in table)
    out.append(CheckResult(
        "capped_pd_bound",
        bounded,
        "each CapPD <= games * 45" + (" (raw blowouts present)" if overflow else ""),
    ))

    district_games = [g for g in games if g.is_final and g.district_game]
    played: dict[str, int] = {}
    for game in district_games:
        played[game.home_id] = played.get(game.home_id, 0) + 1
        played[game.away_id] = played.get(game.away_id, 0) + 1
    district_ok = True
    for row in table:
        dplayed = row.district_wins + row.district_losses + row.district_ties
        if dplayed > played.get(row.team_id, 0):
            district_ok = False
        if dplayed != played.get(row.team_id, 0):
            district_ok = False
    out.append(CheckResult("district_wl_matches_flags", district_ok, "district_game flags vs Dist column"))

    conf_ok = all(
        (r.games_played >= config.confidence_min_games and r.confidence >= config.confidence_flag)
        or r.low_confidence
        or r.games_played >= config.confidence_min_games
        for r in table
    )
    flag_consistent = all(
        r.low_confidence == (
            r.games_played < config.confidence_min_games or r.confidence < config.confidence_flag
        )
        for r in table
    )
    out.append(CheckResult("confidence_flag_consistent", flag_consistent and conf_ok, "low_confidence matches rule"))
    return out


def run_validation(
    *,
    expectations_path: Optional[Path] = None,
    data_dir: Optional[Path] = None,
    config: Optional[EngineConfig] = None,
    through_week: Optional[int] = None,
) -> ValidationReport:
    from sixman_rankings.pipeline import rank_season

    cfg = config or EngineConfig()
    if data_dir is None:
        teams, games, roster, panel, priors = load_sample_dataset()
        exp_path = expectations_path or (DEMO_DATA / "validation_expectations.json")
    else:
        teams, games, roster, panel, priors = load_dataset(
            teams_path=Path(data_dir) / "teams.csv",
            games_path=Path(data_dir) / "games.csv",
            roster_path=Path(data_dir) / "roster_factors.csv" if (Path(data_dir) / "roster_factors.csv").exists() else None,
            panel_path=Path(data_dir) / "panel_adjustments.csv" if (Path(data_dir) / "panel_adjustments.csv").exists() else None,
            priors_path=Path(data_dir) / "priors.csv" if (Path(data_dir) / "priors.csv").exists() else None,
        )
        exp_path = expectations_path or (Path(data_dir) / "validation_expectations.json")

    payload: dict[str, Any] = {}
    if exp_path and Path(exp_path).exists():
        payload = json.loads(Path(exp_path).read_text(encoding="utf-8"))
    week = through_week if through_week is not None else payload.get("through_week")
    table = rank_season(
        teams, games, roster=roster, panel=panel, priors=priors, config=cfg, through_week=week
    )

    report = ValidationReport()
    for check in structural_checks(teams, games, table, cfg):
        report.checks.append(check)
    for exp in payload.get("expectations", []):
        report.checks.append(_eval_expectation(exp, table))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate a six-man ranking season against expectation cards.")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--expectations", default=None)
    parser.add_argument("--through-week", type=int, default=None)
    args = parser.parse_args(argv)
    report = run_validation(
        expectations_path=Path(args.expectations) if args.expectations else None,
        data_dir=Path(args.data_dir) if args.data_dir else None,
        through_week=args.through_week,
    )
    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
