#!/usr/bin/env python3
"""Async runner for semiconductor data analysis skill.

This module includes mock implementations for two backend functions:
1) submit_fab_metric_analysis(user_query) -> run_id
2) query_analysis_status(run_id) -> dict(status, node, payload?)

Replace these two functions with real service calls in production.
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
STATE_DIR = SKILL_ROOT / "state"
RUNS_DIR = STATE_DIR / "runs"
LAST_RUN_FILE = STATE_DIR / "last_run_id.txt"


def _ensure_dirs() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MockJobPlan:
    processing_seconds: int
    report: str
    chart_url: str
    data_message: str


# ---------------------------
# Mock backend functions
# ---------------------------
def submit_fab_metric_analysis(user_query: str) -> str:
    """Mock: submit analysis job and persist initial run state.

    Replace this with your real async submit function.
    """
    _ensure_dirs()
    run_id = f"run_{uuid.uuid4().hex[:10]}"

    processing_seconds = random.randint(60, 240)
    plan = MockJobPlan(
        processing_seconds=processing_seconds,
        report=(
            "[MOCK] Semi metric analysis report\n"
            f"Input: {user_query}\n"
            "- Yield drop correlates with Qtime excursion on litho segment L2.\n"
            "- FDC drift observed on chamber C-17 temperature channel.\n"
            "- Inline CD variance increased for bad wafer population."
        ),
        chart_url=f"https://mock-semi-dashboard.local/reports/{run_id}",
        data_message=(
            "[MOCK] Last 7 days: good wafer pass rate 96.8% -> 94.9%; "
            "bad wafer cluster linked to toolset ETCH-03 / LOT family A19."
        ),
    )

    now = time.time()
    state = {
        "run_id": run_id,
        "query": user_query,
        "created_at": now,
        "updated_at": now,
        "status": "processing",
        "node": "queued",
        "plan": plan.__dict__,
        "history": [
            {"ts": now, "status": "processing", "node": "queued"},
        ],
    }

    _write_state(run_id, state)
    LAST_RUN_FILE.write_text(run_id, encoding="utf-8")
    return run_id


def query_analysis_status(run_id: str) -> Dict[str, Any]:
    """Mock: query job status and update node progression.

    Replace this with your real status query function.
    """
    state = _read_state(run_id)
    if not state:
        return {"run_id": run_id, "status": "failed", "node": "not_found", "error": "run_id not found"}

    if state["status"] in {"success", "failed"}:
        return _public_status(state)

    now = time.time()
    elapsed = now - state["created_at"]
    total = float(state["plan"]["processing_seconds"])
    ratio = elapsed / total if total > 0 else 1.0

    if ratio < 0.25:
        node = "loading_data"
        status = "processing"
    elif ratio < 0.65:
        node = "feature_engineering"
        status = "processing"
    elif ratio < 1.0:
        node = "root_cause_scoring"
        status = "processing"
    else:
        node = "completed"
        status = "success"

    state["status"] = status
    state["node"] = node
    state["updated_at"] = now
    state["history"].append({"ts": now, "status": status, "node": node})

    if status == "success":
        state["result"] = {
            "analysis_report": state["plan"]["report"],
            "chart_link": state["plan"]["chart_url"],
            "data_message": state["plan"]["data_message"],
        }

    _write_state(run_id, state)
    return _public_status(state)


# ---------------------------
# Persistence helpers
# ---------------------------
def _state_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def _read_state(run_id: str) -> Dict[str, Any] | None:
    path = _state_path(run_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(run_id: str, data: Dict[str, Any]) -> None:
    _ensure_dirs()
    path = _state_path(run_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_status(state: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "run_id": state["run_id"],
        "status": state["status"],
        "node": state.get("node", "unknown"),
        "updated_at": state.get("updated_at"),
    }
    if state["status"] == "success":
        payload["result"] = state.get("result", {})
    return payload


# ---------------------------
# CLI commands
# ---------------------------
def cmd_start(args: argparse.Namespace) -> int:
    run_id = submit_fab_metric_analysis(args.query)
    print(json.dumps({"run_id": run_id, "status": "processing"}, ensure_ascii=False))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    data = query_analysis_status(args.run_id)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    start_time = time.time()
    while True:
        data = query_analysis_status(args.run_id)
        print(json.dumps(data, ensure_ascii=False))

        if data.get("status") in {"success", "failed"}:
            return 0

        if time.time() - start_time > args.timeout:
            print(
                json.dumps(
                    {
                        "run_id": args.run_id,
                        "status": "timeout",
                        "message": f"still processing after {args.timeout}s",
                    },
                    ensure_ascii=False,
                )
            )
            return 2

        time.sleep(args.interval)


def cmd_result(args: argparse.Namespace) -> int:
    state = _read_state(args.run_id)
    if not state:
        print(json.dumps({"error": "run_id not found", "run_id": args.run_id}, ensure_ascii=False))
        return 1

    if state.get("status") != "success":
        print(
            json.dumps(
                {
                    "run_id": args.run_id,
                    "status": state.get("status", "unknown"),
                    "node": state.get("node", "unknown"),
                    "message": "result not ready",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(json.dumps(state.get("result", {}), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run semi data analysis workflow.")
    sub = parser.add_subparsers(dest="command", required=True)

    start_p = sub.add_parser("start", help="submit a new analysis run")
    start_p.add_argument("--query", required=True, help="user original message")
    start_p.set_defaults(func=cmd_start)

    status_p = sub.add_parser("status", help="query run status")
    status_p.add_argument("--run-id", required=True)
    status_p.set_defaults(func=cmd_status)

    wait_p = sub.add_parser("wait", help="poll until run completes")
    wait_p.add_argument("--run-id", required=True)
    wait_p.add_argument("--interval", type=int, default=20)
    wait_p.add_argument("--timeout", type=int, default=1200)
    wait_p.set_defaults(func=cmd_wait)

    result_p = sub.add_parser("result", help="get final result")
    result_p.add_argument("--run-id", required=True)
    result_p.set_defaults(func=cmd_result)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
