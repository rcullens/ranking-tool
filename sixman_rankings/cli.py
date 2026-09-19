"""Command-line entry point: ``sixman-rank`` / ``python -m sixman_rankings``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence, TextIO

from sixman_rankings import __version__
from sixman_rankings.classify import group_rows_by_classification
from sixman_rankings.export import (
    RANKING_FIELDS,
    rankings_document,
    write_history_csv,
    write_rankings_csv,
    write_rankings_json,
)
from sixman_rankings.history import (
    district_groups,
    format_rank_delta,
    format_region_label,
    notable_movers,
    power_groups_by_district,
    region_groups,
)
from sixman_rankings.io import load_dataset, load_sample_dataset
from sixman_rankings.models import EngineConfig, RankedTeam
from sixman_rankings.pipeline import RankingEngine
from sixman_rankings.validate import run_validation
from sixman_rankings.whatif import format_what_if, simulate_what_if


def _add_data_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--teams", help="Teams CSV/JSON (default: bundled sample).")
    parser.add_argument("--games", help="Games CSV/JSON (default: bundled sample).")
    parser.add_argument("--roster", help="Roster-turnover CSV/JSON.")
    parser.add_argument("--panel", help="Human-panel adjustment CSV/JSON.")
    parser.add_argument("--priors", help="Previous-season ratings CSV/JSON.")
    parser.add_argument(
        "--data-dir",
        help="Directory containing teams.csv, games.csv, and optional extras.",
    )
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--through-week", type=int, default=None)
    parser.add_argument("--no-panel", action="store_true")
    parser.add_argument("--panel-mix", type=float, default=None)
    parser.add_argument(
        "--home-field",
        type=float,
        default=None,
        help="Home-field Elo edge added to expected spread (default 35; 0 disables).",
    )
    parser.add_argument(
        "--recency-half-life",
        type=float,
        default=None,
        help="Weeks until a game's Elo/SOS weight halves (default 5; 0 disables).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sixman-rank",
        description=(
            "Texas UIL six-man power rankings: mercy-capped differentials, "
            "3-tier SOS, Toy Elo, turnover decay, panel blend, recency, and "
            "week-to-week tooling."
        ),
    )
    parser.add_argument("--version", action="version", version=f"sixman-rankings {__version__}")
    sub = parser.add_subparsers(dest="command")

    rank = sub.add_parser("rank", help="Publish power rankings (default command).")
    _add_data_args(rank)
    rank.add_argument("--format", choices=("table", "csv", "json"), default="table")
    rank.add_argument("--top", type=int, default=None)
    rank.add_argument(
        "--classification",
        default=None,
        help='Filter to a class/division, e.g. "1A DI", "DI", "DII".',
    )
    rank.add_argument("--district", default=None, help='Local power table for one district, e.g. "8-1A DI".')
    rank.add_argument("--region", default=None, help='Local power table for one region, e.g. "west-texas".')
    rank.add_argument(
        "--split",
        action="store_true",
        help="Print a separate table per classification (DI / DII).",
    )
    rank.add_argument(
        "--split-district",
        action="store_true",
        help="Print a local power table (and W-L race) per district.",
    )
    rank.add_argument(
        "--split-region",
        action="store_true",
        help="Print a local power table per region.",
    )
    rank.add_argument("--no-district", action="store_true", help="Hide the district W-L section.")
    rank.add_argument("--no-movement", action="store_true", help="Skip week-over-week deltas.")
    rank.add_argument("--movers", type=int, default=6, help="How many notable movers to list (0 hides).")
    rank.add_argument("--out", help="Write a JSON rankings document to this path.")
    rank.add_argument("--out-csv", help="Write rankings CSV to this path.")
    rank.add_argument("--history-out", help="Write a JSON document that includes weekly history.")
    rank.add_argument("--history-csv", help="Write weekly history as a long CSV.")

    whatif = sub.add_parser("what-if", help="Provisional result; does not mutate the season.")
    _add_data_args(whatif)
    whatif.add_argument("--home", required=True, dest="home_id")
    whatif.add_argument("--away", required=True, dest="away_id")
    whatif.add_argument("--home-score", type=int, default=None)
    whatif.add_argument("--away-score", type=int, default=None)
    whatif.add_argument(
        "--margin",
        type=float,
        default=None,
        help="Home-perspective margin if scores are omitted (capped at 45).",
    )
    whatif.add_argument("--neutral", action="store_true")
    whatif.add_argument("--district-game", action="store_true")

    validate = sub.add_parser("validate", help="Score a season against expectation cards.")
    validate.add_argument("--data-dir", default=None)
    validate.add_argument("--expectations", default=None)
    validate.add_argument("--through-week", type=int, default=None)

    sync = sub.add_parser("sync", help="Pull live scores and republish rankings.")
    sync.add_argument("--data-dir", default=None)
    sync.add_argument("--feed-url", default=None, help="JSON score feed (else SIXMAN_FEED_URL).")
    sync.add_argument("--force", action="store_true", help="Release held demo finals even off-window.")

    serve = sub.add_parser("serve", help="Run the live rankings web app (graph + API).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=43127)
    serve.add_argument("--data-dir", default=None)

    offline = sub.add_parser(
        "export-offline",
        help="Write JSON snapshots for the Android APK / PWA (no server required).",
    )
    offline.add_argument("--out", default="web/public/offline", help="Directory for status.json, boards.json, …")
    offline.add_argument("--data-dir", default=None)
    offline.add_argument("--start-week", type=int, default=None)

    return parser


def _from_data_dir(data_dir: Path) -> dict[str, Optional[Path]]:
    def maybe(name: str) -> Optional[Path]:
        for suffix in (".csv", ".json"):
            path = data_dir / f"{name}{suffix}"
            if path.exists():
                return path
        return None

    teams = maybe("teams")
    games = maybe("games")
    if teams is None or games is None:
        raise SystemExit(f"{data_dir} must contain teams.csv/json and games.csv/json")
    return {
        "teams": teams,
        "games": games,
        "roster": maybe("roster_factors") or maybe("roster"),
        "panel": maybe("panel_adjustments") or maybe("panel"),
        "priors": maybe("priors"),
    }


def load_from_args(args: argparse.Namespace):
    if getattr(args, "teams", None) or getattr(args, "games", None) or getattr(args, "data_dir", None):
        if args.data_dir:
            found = _from_data_dir(Path(args.data_dir))
            teams_p = args.teams or found["teams"]
            games_p = args.games or found["games"]
            roster_p = args.roster or found["roster"]
            panel_p = args.panel or found["panel"]
            priors_p = args.priors or found["priors"]
        else:
            if not args.teams or not args.games:
                raise SystemExit("--teams and --games are required unless you pass --data-dir or use sample data")
            teams_p, games_p = args.teams, args.games
            roster_p, panel_p, priors_p = args.roster, args.panel, args.priors
        return load_dataset(
            teams_path=teams_p,
            games_path=games_p,
            roster_path=roster_p,
            panel_path=None if getattr(args, "no_panel", False) else panel_p,
            priors_path=priors_p,
        )

    teams, games, roster, panel, priors = load_sample_dataset()
    if getattr(args, "no_panel", False):
        panel = []
    return teams, games, roster, panel, priors


def config_from_args(args: argparse.Namespace) -> EngineConfig:
    kwargs: dict = {}
    if getattr(args, "no_panel", False):
        kwargs["panel_mix"] = 0.0
    elif getattr(args, "panel_mix", None) is not None:
        kwargs["panel_mix"] = args.panel_mix
    if getattr(args, "home_field", None) is not None:
        kwargs["home_field"] = args.home_field
    if getattr(args, "recency_half_life", None) is not None:
        kwargs["recency_half_life"] = args.recency_half_life
    return EngineConfig(**kwargs)


def format_table(
    rows: Sequence[RankedTeam],
    *,
    title: str,
    show_district_block: bool = True,
    district_rows: Optional[Sequence[RankedTeam]] = None,
) -> str:
    headers = (
        "Rk",
        "Mv",
        "Team",
        "Rec",
        "Dist",
        "Cls",
        "Power",
        "±",
        "Conf",
        "SOS",
        "Dens",
        "Notes",
    )
    body: list[tuple[str, ...]] = []
    for row in rows:
        mark = "*" if row.low_confidence else ""
        body.append(
            (
                f"{row.rank}{mark}",
                format_rank_delta(row.rank_delta),
                row.name,
                row.record,
                row.district_record,
                row.classification,
                f"{row.power:7.1f}",
                f"{row.sigma:5.1f}",
                f"{row.confidence:4.2f}",
                f"{row.sos:6.2f}",
                f"{row.density:4.2f}",
                row.notes,
            )
        )
    widths = [len(h) for h in headers]
    for line in body:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))

    numeric = {0, 1, 6, 7, 8, 9, 10}

    def fmt(cells: Sequence[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            parts.append(cell.rjust(widths[i]) if i in numeric else cell.ljust(widths[i]))
        return "  ".join(parts)

    rule = "  ".join("-" * w for w in widths)
    out = [
        title,
        "Cap 45  ·  Toy Elo  ·  3-tier SOS  ·  recency  ·  * = low confidence",
        "",
        fmt(headers),
        rule,
    ]
    out.extend(fmt(line) for line in body)

    if show_district_block:
        out.extend(["", "District standings (W-L only; not in the power formula)"])
        for district, members in district_groups(district_rows or rows).items():
            out.append(f"  {district}")
            for row in members:
                out.append(f"    {row.district_record:<7} {row.name}")
    return "\n".join(out)


def emit_table_or_data(
    rows: Sequence[RankedTeam],
    fmt: str,
    dest: TextIO,
    *,
    title: str,
    week: Optional[int],
    season: Optional[int],
    classification: Optional[str],
    show_district_block: bool,
    movers: Sequence[RankedTeam],
    district_rows: Optional[Sequence[RankedTeam]] = None,
) -> None:
    if fmt == "table":
        dest.write(
            format_table(
                rows,
                title=title,
                show_district_block=show_district_block,
                district_rows=district_rows,
            )
            + "\n"
        )
        if movers:
            dest.write("\nNotable movers\n")
            for row in movers:
                dest.write(
                    f"  {format_rank_delta(row.rank_delta):>3}  {row.name}"
                    f"  ({row.prev_rank}→{row.rank}, power {row.power_delta:+.1f})\n"
                )
        return
    import json

    if fmt == "json":
        json.dump(
            rankings_document(rows, week=week, season=season, classification=classification),
            dest,
            indent=2,
        )
        dest.write("\n")
        return
    import csv

    from sixman_rankings.export import ranked_record

    records = [ranked_record(r, week=week, season=season) for r in rows]
    writer = csv.DictWriter(dest, fieldnames=list(RANKING_FIELDS))
    writer.writeheader()
    writer.writerows(records)


def _resolved_week(games, through_week: Optional[int]) -> int:
    if through_week is not None:
        return through_week
    finals = [g.week for g in games if g.is_final]
    return max(finals) if finals else 0


def _run_rank(args: argparse.Namespace) -> int:
    teams, games, roster, panel, priors = load_from_args(args)
    config = config_from_args(args)
    engine = RankingEngine(
        teams, games, roster=roster, panel=panel, priors=priors, config=config, season=args.season
    )
    week = _resolved_week(games, args.through_week)
    history = None
    if args.history_out or args.history_csv or args.split:
        history = engine.weekly_history(week, classification=None)

    title = f"Texas UIL Six-Man Power Rankings  ·  through Week {week}"
    if args.classification and not args.split:
        title += f"  ·  {args.classification}"
    if args.district and not args.split_district:
        title += f"  ·  {args.district}"
    if args.region and not args.split_region:
        title += f"  ·  {format_region_label(args.region)}"

    blocks: list[tuple[str, list[RankedTeam], list[RankedTeam]]]
    if args.split_district:
        overall = engine.rank(
            through_week=week,
            classification=args.classification,
            region=args.region,
            with_movement=False,
        )
        blocks = []
        for label, members in power_groups_by_district(overall).items():
            if args.district and label.lower() != args.district.lower():
                continue
            subset = engine.rank(
                through_week=week,
                classification=args.classification,
                district=label,
                region=args.region,
                with_movement=not args.no_movement,
            )
            full_subset = list(subset)
            if args.top is not None:
                subset = subset[: args.top]
            blocks.append((f"{title}  ·  {label}", subset, full_subset))
        rows = overall
        if not blocks:
            blocks = [(title, overall, overall)]
    elif args.split_region:
        overall = engine.rank(
            through_week=week,
            classification=args.classification,
            district=args.district,
            with_movement=False,
        )
        blocks = []
        for label, members in region_groups(overall).items():
            if args.region and label.lower() != args.region.lower():
                continue
            subset = engine.rank(
                through_week=week,
                classification=args.classification,
                district=args.district,
                region=label,
                with_movement=not args.no_movement,
            )
            full_subset = list(subset)
            if args.top is not None:
                subset = subset[: args.top]
            blocks.append((f"{title}  ·  {format_region_label(label)}", subset, full_subset))
        rows = overall
        if not blocks:
            blocks = [(title, overall, overall)]
    elif args.split:
        overall = engine.rank(through_week=week, with_movement=False)
        labels = sorted(group_rows_by_classification(overall))
        blocks = []
        for label in labels:
            if args.classification:
                from sixman_rankings.classify import classification_matches

                if not classification_matches(label, args.classification):
                    continue
            subset = engine.rank(
                through_week=week,
                classification=label,
                district=args.district,
                region=args.region,
                with_movement=not args.no_movement,
            )
            full_subset = list(subset)
            if args.top is not None:
                subset = subset[: args.top]
            blocks.append((f"{title}  ·  {label}", subset, full_subset))
        rows = overall
        if not blocks:
            blocks = [(title, overall, overall)]
    else:
        rows = engine.rank(
            through_week=week,
            classification=args.classification,
            district=args.district,
            region=args.region,
            with_movement=not args.no_movement,
        )
        full_for_district = list(rows)
        if args.top is not None:
            rows = rows[: args.top]
        blocks = [(title, list(rows), full_for_district)]

    for i, (block_title, block_rows, district_source) in enumerate(blocks):
        if i:
            sys.stdout.write("\n")
        movers = notable_movers(block_rows, limit=args.movers) if args.movers else []
        emit_table_or_data(
            block_rows,
            args.format,
            sys.stdout,
            title=block_title,
            week=week,
            season=args.season,
            classification=args.classification,
            show_district_block=(
                args.format == "table"
                and not args.no_district
                and not args.split
            ),
            movers=movers if args.format == "table" else [],
            district_rows=district_source,
        )

    export_rows = blocks[0][1] if args.split and len(blocks) == 1 else rows
    if args.out:
        write_rankings_json(
            args.out,
            export_rows,
            week=week,
            season=args.season,
            classification=args.classification,
            history=history if args.history_out == args.out else None,
        )
    if args.out_csv:
        write_rankings_csv(args.out_csv, export_rows, week=week, season=args.season)
    if args.history_out:
        hist = history or engine.weekly_history(week)
        write_rankings_json(
            args.history_out,
            export_rows,
            week=week,
            season=args.season,
            classification=args.classification,
            history=hist,
        )
    if args.history_csv:
        hist = history or engine.weekly_history(week)
        write_history_csv(args.history_csv, hist, season=args.season)
    return 0


def _run_what_if(args: argparse.Namespace) -> int:
    teams, games, roster, panel, priors = load_from_args(args)
    config = config_from_args(args)
    report = simulate_what_if(
        teams,
        games,
        home_id=args.home_id,
        away_id=args.away_id,
        home_score=args.home_score,
        away_score=args.away_score,
        margin=args.margin,
        through_week=args.through_week,
        neutral=args.neutral,
        district_game=args.district_game,
        roster=roster,
        panel=panel,
        priors=priors,
        config=config,
        season=args.season,
    )
    sys.stdout.write(format_what_if(report) + "\n")
    return 0


def _run_sync(args: argparse.Namespace) -> int:
    import os

    from sixman_rankings.live.service import LiveSeasonService, reset_service

    if args.feed_url:
        os.environ["SIXMAN_FEED_URL"] = args.feed_url
    reset_service()
    if args.data_dir:
        service = LiveSeasonService.from_data_dir(args.data_dir)
    else:
        service = LiveSeasonService.from_sample()
    status = service.sync(force_replay=args.force)
    sys.stdout.write(
        f"Week {status.current_week}  ·  {status.last_result}  ·  "
        f"{status.finals} finals / {status.scheduled} scheduled\n"
    )
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    import os

    if args.data_dir:
        os.environ["SIXMAN_DATA_DIR"] = args.data_dir
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("Install the web extra: pip install -e '.[web]'") from exc
    uvicorn.run("sixman_rankings.web.app:app", host=args.host, port=args.port, reload=False)
    return 0


def _run_export_offline(args: argparse.Namespace) -> int:
    from sixman_rankings.live.service import LiveSeasonService
    from sixman_rankings.offline import write_offline_bundle

    if args.data_dir:
        service = LiveSeasonService.from_data_dir(args.data_dir, start_week=args.start_week)
    else:
        service = LiveSeasonService.from_sample(start_week=args.start_week)
    dest = write_offline_bundle(args.out, service=service)
    sys.stdout.write(f"Wrote offline bundle to {dest}\n")
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    from pathlib import Path as P

    report = run_validation(
        expectations_path=P(args.expectations) if args.expectations else None,
        data_dir=P(args.data_dir) if args.data_dir else None,
        through_week=args.through_week,
    )
    sys.stdout.write(report.summary() + "\n")
    return 0 if report.ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    commands = {"rank", "what-if", "validate", "sync", "serve", "export-offline"}
    if not raw or raw[0] not in commands:
        raw = ["rank", *raw]
    args = build_parser().parse_args(raw)
    if args.command == "what-if":
        return _run_what_if(args)
    if args.command == "validate":
        return _run_validate(args)
    if args.command == "sync":
        return _run_sync(args)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "export-offline":
        return _run_export_offline(args)
    return _run_rank(args)


if __name__ == "__main__":
    raise SystemExit(main())
