#!/usr/bin/env python3
"""Rebuild the bundled UIL 1A field from live MaxPreps / SMF (or cached weeks)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sixman_rankings.live.ingest import run_ingest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use cached SMF weeks only (no MaxPreps).")
    parser.add_argument("--skip-smf", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--export-offline", action="store_true")
    args = parser.parse_args()
    report = run_ingest(
        write=not args.no_write,
        export_offline=args.export_offline,
        skip_maxpreps=args.offline,
        skip_smf=args.skip_smf,
        persist_smf=True,
    )
    print(report.summary())
    aquilla = next(s for s in __import__("sixman_rankings.catalog", fromlist=["uil_schools"]).uil_schools() if s.team_id == "aquilla")
    print(f"Aquilla: {aquilla.district} {aquilla.classification} region={aquilla.region}")
    return 0 if report.teams else 1


if __name__ == "__main__":
    raise SystemExit(main())
