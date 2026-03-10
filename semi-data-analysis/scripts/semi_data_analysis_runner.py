#!/usr/bin/env python3
"""Mock async orchestrator for semiconductor data analysis skill.

Replace mock_* functions with real backend integrations.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> float:
    return time.time()


def _run_file(runid: str) -> Path:
    return STATE_DIR / f"run_{runid}.json"


def _save_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------
# Mock backend functions
# ---------------------
def mock_start_analysis(user_query: str) -> str:
    """Mock start function.

    Real-world equivalent:
        runid = start_analysis(user_query)
    """
    runid = f"semi-{uuid.uuid4().hex[:10]}"
    duration_s = 120.0  # change as needed; replace with real async backend behavior

    job = {
        "runid": runid,
        "query": user_query,
        "created_at": _now(),
        "expected_duration_s": duration_s,
        "status": "processing",
        "node_info": {
            "current_node": "dispatch",
            "progress": 0,
            "message": "Job accepted and queued.",
        },
        "result": None,
        "updated_at": _now(),
    }
    _save_json(_run_file(runid), job)
    _save_json(STATE_DIR / "latest_run.json", {"runid": runid, "updated_at": _now()})
    return runid


def mock_query_status(runid: str) -> Dict[str, Any]:
    """Mock status function.

    Real-world equivalent:
        payload = query_status(runid)
        # payload contains status + node info (+ final data on success)
    """
    path = _run_file(runid)
    if not path.exists():
        return {
            "runid": runid,
            "status": "failed",
            "node_info": {"current_node": "unknown", "message": "runid not found"},
        }

    job = _load_json(path)
    elapsed = max(0.0, _now() - float(job["created_at"]))
    expected = max(1.0, float(job.get("expected_duration_s", 120.0)))
    pct = min(100, int(elapsed / expected * 100))

    if pct < 25:
        node = {"current_node": "extract", "progress": pct, "message": "Extracting fab datasets (FDC/Qtime/Inline/commonality)."}
        status = "processing"
    elif pct < 70:
        node = {"current_node": "feature_engineering", "progress": pct, "message": "Computing lot/wafer-level indicators and drift signals."}
        status = "processing"
    elif pct < 100:
        node = {"current_node": "root_cause_ranking", "progress": pct, "message": "Ranking potential root causes and generating figures."}
        status = "processing"
    else:
        node = {"current_node": "finalize", "progress": 100, "message": "Analysis completed."}
        status = "success"

    result = None
    if status == "success":
        result = {
            "analysis_report": (
                "Bad wafer rate increased by 2.8% WoW. Top contributors: "
                "ETCH-12 chamber pressure drift (38%), Qtime hold at CMP->CLEAN step (31%), "
                "and Inline CD variance excursion on layer M3 (17%)."
            ),
            "chart_url": f"https://mock-semi-dashboard.local/report/{runid}",
            "data_message": (
                "Compared with good wafers, bad wafers show +1.9σ pressure instability on ETCH-12, "
                "+23min median Qtime at CMP->CLEAN, and +14% Inline CD 95th percentile for M3 lots."
            ),
        }

    payload = {
        "runid": runid,
        "status": status,
        "node_info": node,
        "result": result,
        "updated_at": _now(),
    }

    job.update(payload)
    _save_json(path, job)
    _save_json(STATE_DIR / "latest_run.json", {"runid": runid, "updated_at": _now()})
    return payload


def _get_latest_runid() -> str | None:
    latest = STATE_DIR / "latest_run.json"
    if not latest.exists():
        return None
    payload = _load_json(latest)
    return payload.get("runid")


def cmd_start(args: argparse.Namespace) -> int:
    runid = mock_start_analysis(args.query)
    payload = mock_query_status(runid)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    runid = args.runid or _get_latest_runid()
    if not runid:
        print(json.dumps({"error": "no runid provided and no latest_run.json found"}, ensure_ascii=False, indent=2))
        return 1
    payload = mock_query_status(runid)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_wait(args: argparse.Namespace) -> int:
    runid = args.runid or _get_latest_runid()
    if not runid:
        print(json.dumps({"error": "no runid provided and no latest_run.json found"}, ensure_ascii=False, indent=2))
        return 1

    start_t = _now()
    while True:
        payload = mock_query_status(runid)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if payload.get("status") in {"success", "failed"}:
            return 0
        if (_now() - start_t) > args.timeout:
            print(json.dumps({"runid": runid, "status": "timeout"}, ensure_ascii=False, indent=2))
            return 2
        time.sleep(args.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi data analysis async mock runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="start a new analysis")
    p_start.add_argument("--query", required=True, help="raw user natural language query")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="query status by runid or latest")
    p_status.add_argument("--runid", default=None)
    p_status.set_defaults(func=cmd_status)

    p_wait = sub.add_parser("wait", help="poll status until success/failed/timeout")
    p_wait.add_argument("--runid", default=None)
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
