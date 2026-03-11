#!/usr/bin/env python3
"""Semi OP case async orchestrator with mock start/query functions.

Replace `mock_start_analysis` and `mock_query_status` with your real service calls.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

RUNTIME_DIR = Path("runtime/op_case_runs")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------
# Mock functions (replace with your real APIs)
# --------------------
def mock_start_analysis(user_query: str) -> str:
    """Start analysis task and return run_id."""
    run_id = f"semi-{uuid.uuid4().hex[:12]}"
    duration_s = int(os.getenv("MOCK_DURATION_S", "45"))
    init_state = {
        "run_id": run_id,
        "status": "processing",
        "node": "ingest_fdc_qtime_inline_commonality",
        "submitted_query": user_query,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "_mock_duration_s": duration_s,
        "_mock_started_at": time.time(),
    }
    _write_json(RUNTIME_DIR / f"{run_id}.json", init_state)
    _write_json(RUNTIME_DIR / "latest_run.json", {"run_id": run_id, "updated_at": utc_now()})
    return run_id


def mock_query_status(run_id: str) -> Dict[str, Any]:
    """Query task status by run_id, returning processing/success payload."""
    run_file = RUNTIME_DIR / f"{run_id}.json"
    if not run_file.exists():
        return {"run_id": run_id, "status": "failed", "error": "run_id not found"}

    state = _read_json(run_file)
    elapsed = time.time() - state.get("_mock_started_at", time.time())
    duration_s = state.get("_mock_duration_s", 45)

    if elapsed < duration_s:
        progress = min(95, int((elapsed / duration_s) * 100))
        state.update(
            {
                "status": "processing",
                "node": f"root_cause_modeling_{progress}pct",
                "updated_at": utc_now(),
            }
        )
    else:
        state.update(
            {
                "status": "success",
                "node": "completed",
                "report": (
                    "检测到Bad wafer在ETCH-03机台段出现显著偏移："
                    "FDC温控漂移与Qtime超阈值共同放大失效风险，"
                    "Inline缺陷率在对应批次提升。"
                ),
                "chart_url": f"https://example.com/semi-analysis/{run_id}",
                "data_message": (
                    "最近24h样本中，Bad wafer组Qtime均值较Good wafer高18.7%，"
                    "且FDC压力波动σ增大约1.4倍，建议优先检查ETCH-03腔体维护窗口。"
                ),
                "updated_at": utc_now(),
            }
        )

    _write_json(run_file, state)
    _write_json(
        RUNTIME_DIR / "latest_run.json",
        {"run_id": run_id, "last_snapshot": state, "updated_at": utc_now()},
    )

    return {
        "run_id": run_id,
        "status": state["status"],
        "node": state.get("node"),
        "report": state.get("report"),
        "chart_url": state.get("chart_url"),
        "data_message": state.get("data_message"),
        "updated_at": state.get("updated_at"),
    }


# --------------------
# Orchestration helpers
# --------------------
def start_run(user_query: str) -> Dict[str, Any]:
    run_id = mock_start_analysis(user_query)
    return {"run_id": run_id, "status": "processing", "message": "analysis started"}


def query_run(run_id: str) -> Dict[str, Any]:
    return mock_query_status(run_id)


def watch_run(run_id: str, interval_s: int = 20, timeout_s: int = 1800) -> Dict[str, Any]:
    start_ts = time.time()
    while True:
        snapshot = query_run(run_id)
        if snapshot.get("status") in {"success", "failed"}:
            return snapshot

        if time.time() - start_ts > timeout_s:
            timeout_payload = {
                "run_id": run_id,
                "status": "processing",
                "node": "timeout_waiting_for_completion",
                "message": f"Polling timed out after {timeout_s}s",
                "updated_at": utc_now(),
            }
            _write_json(RUNTIME_DIR / f"{run_id}.json", timeout_payload)
            return timeout_payload

        time.sleep(interval_s)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi OP case async runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="start a new run")
    p_start.add_argument("query", help="raw user natural-language query")

    p_query = sub.add_parser("query", help="query run status")
    p_query.add_argument("run_id", help="run id")

    p_watch = sub.add_parser("watch", help="poll until success/failed/timeout")
    p_watch.add_argument("run_id", help="run id")
    p_watch.add_argument("--interval", type=int, default=20, help="poll interval in seconds")
    p_watch.add_argument("--timeout", type=int, default=1800, help="poll timeout in seconds")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "start":
        out = start_run(args.query)
    elif args.command == "query":
        out = query_run(args.run_id)
    else:
        out = watch_run(args.run_id, interval_s=args.interval, timeout_s=args.timeout)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
