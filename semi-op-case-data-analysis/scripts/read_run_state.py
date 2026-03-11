#!/usr/bin/env python3
"""Read local persisted run state for a given run_id."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

RUNTIME_DIR = Path("runtime/op_case_runs")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read persisted OP case state")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--history", action="store_true", help="Print full history")
    args = parser.parse_args()

    state_file = RUNTIME_DIR / f"{args.run_id}.json"
    if not state_file.exists():
        raise SystemExit(f"state file not found: {state_file}")

    data = json.loads(state_file.read_text(encoding="utf-8"))
    if args.history:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"run_id": data["run_id"], "latest": data.get("latest", {})}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
