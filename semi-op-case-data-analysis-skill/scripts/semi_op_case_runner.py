#!/usr/bin/env python3
"""Mock runner for semi OP case async analysis workflow.

Replace `start_analysis_task` and `query_analysis_status` with real function calls.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_analysis_task(user_query: str) -> str:
    """Mock task start function.

    Real behavior expected:
      input: user's natural-language query
      output: run_id
    """
    _ = user_query
    return f"run_{uuid.uuid4().hex[:12]}"


def query_analysis_status(run_id: str) -> Dict[str, Any]:
    """Mock status query function.

    Real behavior expected:
      input: run_id
      output: dict with status field; when success includes report/link/message.

    This mock simulates processing for first ~90 seconds from first seen timestamp,
    then returns success.
    """
    state_dir = Path(__file__).resolve().parents[1] / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    meta_file = state_dir / f"{run_id}.meta.json"

    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
    else:
        meta = {"first_seen_ts": time.time()}
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - float(meta["first_seen_ts"])

    if elapsed < 90:
        return {
            "run_id": run_id,
            "status": "processing",
            "node": "feature_engineering",
            "message": f"Task is processing, elapsed={int(elapsed)}s",
            "updated_at": now_iso(),
        }

    return {
        "run_id": run_id,
        "status": "success",
        "kpi_report": (
            "Qtime 在 LOT_A12 工序出现异常抬升，叠加 FDC 温漂告警后，"
            "Bad wafer 比例较基线提升 3.8%。Inline 厚度偏移与 commonality 机台群组 M-07 高度相关。"
        ),
        "chart_link": "https://mock.local/semi/op-case/charts/run_id",
        "data_message": "2026-01-14 08:00~12:00 区间，机台 M-07 的异常批次占比 27%，对应良率下降 2.3pp。",
        "updated_at": now_iso(),
    }


def persist_status(state_dir: Path, run_id: str, status_payload: Dict[str, Any]) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{run_id}.json"
    state_file.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (state_dir / "latest_run_id.txt").write_text(run_id, encoding="utf-8")
    return state_file


def watch_run(run_id: str, poll_interval_s: int, timeout_s: int, state_dir: Path) -> Dict[str, Any]:
    start_ts = time.time()
    while True:
        payload = query_analysis_status(run_id)
        persist_status(state_dir, run_id, payload)

        if payload.get("status") in {"success", "failed", "error"}:
            return payload

        if time.time() - start_ts > timeout_s:
            payload["status"] = "timeout"
            payload["message"] = "Polling timed out. You can continue polling later with the same run_id."
            persist_status(state_dir, run_id, payload)
            return payload

        time.sleep(poll_interval_s)


def main() -> None:
    parser = argparse.ArgumentParser(description="Semi OP case async analysis runner (mock).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    start_p = sub.add_parser("start", help="Start a new analysis task with a user query.")
    start_p.add_argument("query", help="Raw user natural-language query.")
    start_p.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))

    status_p = sub.add_parser("status", help="Query status for a run_id once and persist it.")
    status_p.add_argument("run_id")
    status_p.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))

    watch_p = sub.add_parser("watch", help="Poll until completion/timeout and persist status updates.")
    watch_p.add_argument("run_id")
    watch_p.add_argument("--poll-interval", type=int, default=30)
    watch_p.add_argument("--timeout", type=int, default=1200)
    watch_p.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))

    args = parser.parse_args()
    state_dir = Path(args.state_dir)

    if args.cmd == "start":
        run_id = start_analysis_task(args.query)
        payload = {
            "run_id": run_id,
            "status": "submitted",
            "message": "Task submitted successfully. Use status/watch to track progress.",
            "query": args.query,
            "updated_at": now_iso(),
        }
        state_file = persist_status(state_dir, run_id, payload)
        print(json.dumps({"run_id": run_id, "state_file": str(state_file)}, ensure_ascii=False))
        return

    if args.cmd == "status":
        payload = query_analysis_status(args.run_id)
        state_file = persist_status(state_dir, args.run_id, payload)
        print(json.dumps({"payload": payload, "state_file": str(state_file)}, ensure_ascii=False))
        return

    if args.cmd == "watch":
        payload = watch_run(args.run_id, args.poll_interval, args.timeout, state_dir)
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
