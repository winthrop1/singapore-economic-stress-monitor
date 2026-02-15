#!/usr/bin/env python3
"""
Generate frontend JSON payloads from backend pipeline outputs.

Default targets:
- frontend/public/projects/singapore-economic-stress-monitor/data
- output/dashboard_data
"""

import argparse
import os
from typing import List

import config
from main import run_dashboard
from src.frontend_data import build_frontend_payload, write_frontend_payload


def _default_targets() -> List[str]:
    return [
        os.path.join(
            config.BASE_DIR,
            "frontend",
            "public",
            "projects",
            "singapore-economic-stress-monitor",
            "data",
        ),
        os.path.join(config.BASE_DIR, "output", "dashboard_data"),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export backend results to frontend JSON payloads.")
    parser.add_argument(
        "--target",
        action="append",
        dest="targets",
        help="Output directory to write latest.json/history.json/indicators.json. Can be provided multiple times.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed pipeline output.",
    )

    args = parser.parse_args()
    targets = args.targets if args.targets else _default_targets()

    results = run_dashboard(create_charts=False, verbose=not args.quiet)
    payload = build_frontend_payload(results["stress_df"])

    print("\nExporting frontend payload files:")
    for target in targets:
        latest_path, history_path, indicators_path = write_frontend_payload(payload, target)
        print(f"  ✓ {latest_path}")
        print(f"  ✓ {history_path}")
        print(f"  ✓ {indicators_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
