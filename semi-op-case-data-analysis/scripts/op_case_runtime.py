#!/usr/bin/env python3
"""Runtime helpers for semi op case async analysis workflow.

This script provides:
1) mock task start function (returns run_id)
2) mock task status query function (returns status dict)
3) local state persistence + polling workflow

Replace `start_analysis_task` and `query_analysis_status` with real functions while
keeping signatures unchanged.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path("runtime/op_case_runs")
MOCK_TASK_DB = RUNTIME_DIR / "_mock_tasks.json"


@dataclass
class RuntimeConfig:
    interval_s: int = 30
    timeout_s: int = 20 * 60


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _load_mock_db() -> dict[str, Any]:
    _ensure_runtime_dir()
    if not MOCK_TASK_DB.exists():
        return {}
    return json.loads(MOCK_TASK_DB.read_text(encoding="utf-8"))


def _save_mock_db(data: dict[str, Any]) -> None:
    _ensure_runtime_dir()
    MOCK_TASK_DB.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def start_analysis_task(user_query: str) -> str:
    """Mock: submit long-running analysis task and return run_id.

    Replace with your real start function implementation.
    """
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    mock_db = _load_mock_db()
    mock_db[run_id] = {
        "query": user_query,
        "start_ts": time.time(),
        "phases": [
            (0, "task_queued", 0.05),
            (30, "fdc_qtime_loading", 0.20),
            (90, "inline_feature_join", 0.45),
            (180, "good_bad_wafer_compare", 0.70),
            (300, "commonality_rootcause", 0.90),
            (420, "reporting", 1.0),
        ],
    }
    _save_mock_db(mock_db)
    return run_id


def query_analysis_status(run_id: str) -> dict[str, Any]:
    """Mock: query task status by run_id.

    Replace with your real status function implementation.
    """
    mock_db = _load_mock_db()
    if run_id not in mock_db:
        return {
            "status": "failed",
            "error": f"run_id not found: {run_id}",
        }

    task = mock_db[run_id]
    elapsed = int(time.time() - task["start_ts"])
    phase_name = "task_queued"
    progress = 0.0
    for threshold, name, ratio in task["phases"]:
        if elapsed >= threshold:
            phase_name = name
            progress = ratio

    if elapsed < task["phases"][-1][0]:
        return {
            "status": "processing",
            "node": phase_name,
            "progress": round(progress, 2),
            "elapsed_seconds": elapsed,
        }

    query = task["query"]
    return {
        "status": "success",
        "node": "completed",
        "progress": 1.0,
        "metric_report": (
            "[Mock报告] Good wafer 与 Bad wafer 在关键FDC波动指数上存在显著分离；"
            "Qtime在扩散后段出现长尾，疑似触发Inline缺陷密度上升。"
        ),
        "chart_link": f"https://example.local/op_case/{run_id}/dashboard",
        "data_message": (
            f"[Mock数据消息] 针对请求“{query[:120]}”，系统识别到3个高风险机台组合，"
            "其中Tool-A12在最近24h内与Bad wafer聚类关联度最高。"
        ),
        "elapsed_seconds": elapsed,
    }


def _status_file(run_id: str) -> Path:
    return RUNTIME_DIR / f"{run_id}.json"


def _append_status_snapshot(run_id: str, payload: dict[str, Any]) -> Path:
    _ensure_runtime_dir()
    path = _status_file(run_id)

    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    else:
        state = {
            "run_id": run_id,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "latest": {},
            "history": [],
        }

    snap = {"ts": now_iso(), **payload}
    state["updated_at"] = snap["ts"]
    state["latest"] = payload
    state["history"].append(snap)

    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def start_command(query: str) -> None:
    run_id = start_analysis_task(query)
    state_path = _append_status_snapshot(run_id, {"status": "processing", "node": "submitted"})
    print(json.dumps({"run_id": run_id, "state_file": str(state_path)}, ensure_ascii=False))


def poll_command(run_id: str) -> None:
    payload = query_analysis_status(run_id)
    state_path = _append_status_snapshot(run_id, payload)
    print(
        json.dumps(
            {"run_id": run_id, "state_file": str(state_path), "result": payload},
            ensure_ascii=False,
        )
    )


def watch_command(query: str, config: RuntimeConfig) -> None:
    run_id = start_analysis_task(query)
    _append_status_snapshot(run_id, {"status": "processing", "node": "submitted"})
    print(json.dumps({"run_id": run_id, "event": "started"}, ensure_ascii=False))

    start_ts = time.time()
    while True:
        payload = query_analysis_status(run_id)
        _append_status_snapshot(run_id, payload)
        print(json.dumps({"run_id": run_id, "result": payload}, ensure_ascii=False))

        if payload.get("status") in {"success", "failed"}:
            break
        if (time.time() - start_ts) > config.timeout_s:
            timeout_payload = {
                "status": "timeout",
                "message": f"watch timeout after {config.timeout_s}s",
            }
            _append_status_snapshot(run_id, timeout_payload)
            print(json.dumps({"run_id": run_id, "result": timeout_payload}, ensure_ascii=False))
            break

        time.sleep(config.interval_s)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi OP case runtime helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start analysis task")
    p_start.add_argument("--query", required=True, help="User original query")

    p_poll = sub.add_parser("poll", help="Poll status by run_id")
    p_poll.add_argument("--run-id", required=True)

    p_watch = sub.add_parser("watch", help="Start and wait until finish")
    p_watch.add_argument("--query", required=True)
    p_watch.add_argument("--interval", type=int, default=30)
    p_watch.add_argument("--timeout", type=int, default=20 * 60)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "start":
        start_command(args.query)
    elif args.command == "poll":
        poll_command(args.run_id)
    else:
        watch_command(
            args.query,
            RuntimeConfig(interval_s=args.interval, timeout_s=args.timeout),
        )


if __name__ == "__main__":
    main()
