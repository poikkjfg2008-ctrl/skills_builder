#!/usr/bin/env python3
"""Mock async runner for semiconductor FDC/Qtime/Inline/commonality analysis.

This file is intentionally designed so the two core functions can be replaced by
real service calls later:
- run_semiconductor_analysis(query: str)
- query_analysis_status(run_id: str)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict


def _state_file(state_dir: Path, run_id: str) -> Path:
    return state_dir / f"{run_id}.json"


def _validate_run_id(run_id: str) -> str:
    """Allow only safe run_id characters to prevent path traversal."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError(f"invalid run_id: {run_id}")
    return run_id


def _load_state(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _deterministic_eta(query: str) -> int:
    # 90~240 seconds mock runtime based on query hash (stable for demos/tests)
    digest = hashlib.md5(query.encode("utf-8")).hexdigest()
    return 90 + (int(digest[:4], 16) % 151)


# -----------------------------
# Mock functions to be replaced
# -----------------------------
def run_semiconductor_analysis(query: str, state_dir: Path) -> Dict[str, Any]:
    """Start analysis and return immediate run metadata.

    Production replacement:
    - call your real submission function with `query`
    - keep returned schema compatible with caller logic
    """
    run_id = f"semi-{uuid.uuid4().hex[:12]}"
    now = int(time.time())
    eta_seconds = _deterministic_eta(query)

    state = {
        "run_id": run_id,
        "query": query,
        "status": "processing",
        "created_at": now,
        "eta_seconds": eta_seconds,
        "last_update": now,
        "node": {
            "stage": "queued",
            "message": "任务已提交，等待调度。",
            "progress": 0,
        },
        "result": None,
    }
    _save_state(_state_file(state_dir, run_id), state)

    return {
        "run_id": run_id,
        "status": "processing",
        "eta_seconds": eta_seconds,
        "message": "analysis submitted",
        "state_file": str(_state_file(state_dir, run_id)),
    }


def query_analysis_status(run_id: str, state_dir: Path) -> Dict[str, Any]:
    """Query run status and update progress in state file.

    Production replacement:
    - call your real status API with `run_id`
    - map API response to this returned schema
    """
    run_id = _validate_run_id(run_id)
    path = _state_file(state_dir, run_id)
    if not path.exists():
        raise FileNotFoundError(f"run_id not found: {run_id}")

    state = _load_state(path)
    now = int(time.time())
    elapsed = max(0, now - int(state["created_at"]))
    eta = int(state["eta_seconds"])
    progress = min(100, int(elapsed * 100 / max(1, eta)))

    if progress < 25:
        node = {"stage": "queued", "message": "任务排队中", "progress": progress}
    elif progress < 65:
        node = {"stage": "extract", "message": "抽取FDC/Qtime/Inline/commonality数据", "progress": progress}
    elif progress < 100:
        node = {"stage": "analyze", "message": "执行良率根因分析与图表生成", "progress": progress}
    else:
        node = {"stage": "finalize", "message": "分析完成", "progress": 100}

    state["last_update"] = now
    state["node"] = node

    if progress >= 100 and state["status"] != "success":
        q = state["query"]
        state["status"] = "success"
        state["result"] = {
            "report": f"[Mock报告] 已完成对问题“{q}”的指标分析：主要异常集中在Qtime超时与Inline缺陷密度抬升。",
            "chart_url": f"https://mock-semi-dashboard.local/report/{run_id}",
            "data_message": "[Mock数据消息] Lot L24031 在ETCH-07机台的FDC温控波动σ=2.4x，Bad wafer占比提升至18.7%。",
        }

    _save_state(path, state)

    return {
        "run_id": run_id,
        "status": state["status"],
        "node": state["node"],
        "result": state["result"],
        "state_file": str(path),
        "last_update": state["last_update"],
    }


# -----------------------------
# CLI
# -----------------------------
def cmd_start(args: argparse.Namespace) -> int:
    payload = run_semiconductor_analysis(args.query, Path(args.state_dir))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    payload = query_analysis_status(args.run_id, Path(args.state_dir))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    deadline = time.time() + args.timeout
    while True:
        payload = query_analysis_status(args.run_id, Path(args.state_dir))
        print(json.dumps(payload, ensure_ascii=False))
        if payload["status"] == "success":
            return 0
        if time.time() >= deadline:
            print(json.dumps({"error": "timeout", "run_id": args.run_id}, ensure_ascii=False))
            return 2
        time.sleep(args.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mock semiconductor analysis async runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="submit analysis job")
    p_start.add_argument("--query", required=True, help="raw user natural language query")
    p_start.add_argument("--state-dir", default=".semi_skill_state", help="directory to persist run state")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="query status by run_id")
    p_status.add_argument("--run-id", required=True)
    p_status.add_argument("--state-dir", default=".semi_skill_state")
    p_status.set_defaults(func=cmd_status)

    p_wait = sub.add_parser("wait", help="poll until success or timeout")
    p_wait.add_argument("--run-id", required=True)
    p_wait.add_argument("--state-dir", default=".semi_skill_state")
    p_wait.add_argument("--interval", type=int, default=20)
    p_wait.add_argument("--timeout", type=int, default=1800)
    p_wait.set_defaults(func=cmd_wait)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
