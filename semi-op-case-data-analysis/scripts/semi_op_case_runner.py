#!/usr/bin/env python3
"""Runner for semi OP case async workflow.

Examples:
  python scripts/semi_op_case_runner.py start --query "请分析A17 lot良率波动"
  python scripts/semi_op_case_runner.py poll --run-id semi-xxxx --interval 10 --timeout 1200
  python scripts/semi_op_case_runner.py show --run-id semi-xxxx
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from mock_semi_api import query_analysis_job, start_analysis_job

DEFAULT_STATE_DIR = Path(".skill_state/semi_op_case")


def _state_file(run_id: str, state_dir: Path) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{run_id}.json"


def _write_state(run_id: str, payload: dict, state_dir: Path) -> Path:
    path = _state_file(run_id, state_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cmd_start(args: argparse.Namespace) -> None:
    run_id = start_analysis_job(args.query)
    first_status = {"run_id": run_id, "status": "processing", "node": "submitted"}
    path = _write_state(run_id, first_status, args.state_dir)
    print(json.dumps({"run_id": run_id, "state_file": str(path)}, ensure_ascii=False))


def cmd_poll(args: argparse.Namespace) -> None:
    start_ts = time.time()
    while True:
        payload = query_analysis_job(args.run_id)
        path = _write_state(args.run_id, payload, args.state_dir)
        print(json.dumps({"status": payload.get("status"), "state_file": str(path)}, ensure_ascii=False))

        status = payload.get("status")
        if status in {"success", "failed"}:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if time.time() - start_ts > args.timeout:
            print(json.dumps({"run_id": args.run_id, "status": "timeout"}, ensure_ascii=False))
            return

        time.sleep(args.interval)


def cmd_show(args: argparse.Namespace) -> None:
    path = _state_file(args.run_id, args.state_dir)
    if not path.exists():
        print(json.dumps({"run_id": args.run_id, "status": "missing_state_file"}, ensure_ascii=False))
        return

    print(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi OP case async runner")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        help="Directory to persist status JSON files",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_start = subparsers.add_parser("start", help="Start an analysis task")
    p_start.add_argument("--query", required=True, help="Raw user NL query")
    p_start.set_defaults(func=cmd_start)

    p_poll = subparsers.add_parser("poll", help="Poll task status until terminal state")
    p_poll.add_argument("--run-id", required=True)
    p_poll.add_argument("--interval", type=int, default=10)
    p_poll.add_argument("--timeout", type=int, default=1800)
    p_poll.set_defaults(func=cmd_poll)

    p_show = subparsers.add_parser("show", help="Show latest persisted status")
    p_show.add_argument("--run-id", required=True)
    p_show.set_defaults(func=cmd_show)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
