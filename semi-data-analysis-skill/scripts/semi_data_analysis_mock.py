#!/usr/bin/env python3
"""Mock async runner for semiconductor data analysis skill.

Replace `start_analysis` and `query_status` with real backend calls in production.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

RUNTIME_DIR = Path("runtime/semi_data_analysis")
LATEST_FILE = RUNTIME_DIR / "latest_run.json"
PROCESSING_SECONDS = 20


@dataclass
class NodeInfo:
    current_node: str
    progress: float
    message: str


@dataclass
class AnalysisResult:
    analysis_report: str
    chart_url: str
    data_message: str


@dataclass
class RunState:
    run_id: str
    query: str
    status: str
    node_info: NodeInfo
    result: AnalysisResult
    started_at: str
    updated_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _state_file(run_id: str) -> Path:
    return RUNTIME_DIR / f"{run_id}.json"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(state: RunState) -> None:
    _ensure_runtime_dir()
    _write_json(_state_file(state.run_id), asdict(state))
    _write_json(LATEST_FILE, {"run_id": state.run_id, "updated_at": state.updated_at})


def load_state(run_id: str) -> RunState:
    file = _state_file(run_id)
    if not file.exists():
        raise FileNotFoundError(f"Run ID not found: {run_id}")
    data = _read_json(file)
    return RunState(
        run_id=data["run_id"],
        query=data["query"],
        status=data["status"],
        node_info=NodeInfo(**data["node_info"]),
        result=AnalysisResult(**data["result"]),
        started_at=data["started_at"],
        updated_at=data["updated_at"],
    )


def generate_mock_result(query: str) -> AnalysisResult:
    return AnalysisResult(
        analysis_report=(
            "在最近分析窗口内，Bad wafer占比显著提升；"
            "FDC波动在CMP-03机台最明显，Qtime在清洗至量测段出现拉长。"
            "建议优先检查CMP-03抛光压力与上游等待时间。"
        ),
        chart_url=f"https://mock-semi-dashboard.local/report/{uuid.uuid4().hex[:8]}",
        data_message=f"查询‘{query}’命中12个异常批次，其中7批次集中在夜班时段。",
    )


def start_analysis(query: str) -> Dict[str, Any]:
    """Mock start function: returns run_id quickly and persists processing state."""
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    now = _utc_now()
    state = RunState(
        run_id=run_id,
        query=query,
        status="processing",
        node_info=NodeInfo(
            current_node="task_submitted",
            progress=0.05,
            message="任务已提交，等待后端资源调度",
        ),
        result=AnalysisResult("", "", ""),
        started_at=now,
        updated_at=now,
    )
    _save_state(state)
    return {"run_id": run_id, "status": "processing"}


def query_status(run_id: str) -> Dict[str, Any]:
    """Mock status query: transitions to success after PROCESSING_SECONDS."""
    state = load_state(run_id)
    start_ts = datetime.fromisoformat(state.started_at).timestamp()
    elapsed = max(0.0, time.time() - start_ts)

    if elapsed >= PROCESSING_SECONDS:
        if state.status != "success":
            state.status = "success"
            state.node_info = NodeInfo(
                current_node="completed",
                progress=1.0,
                message="分析完成",
            )
            state.result = generate_mock_result(state.query)
            state.updated_at = _utc_now()
            _save_state(state)
    else:
        state.status = "processing"
        progress = min(0.95, 0.05 + elapsed / PROCESSING_SECONDS * 0.9)
        if progress < 0.4:
            node = "feature_aggregation"
            msg = "正在聚合FDC/Inline/commonality特征"
        elif progress < 0.75:
            node = "qtime_correlation"
            msg = "正在计算Qtime与Bad wafer相关性"
        else:
            node = "report_synthesis"
            msg = "正在生成指标分析报告"
        state.node_info = NodeInfo(current_node=node, progress=round(progress, 3), message=msg)
        state.updated_at = _utc_now()
        _save_state(state)

    return {
        "run_id": state.run_id,
        "status": state.status,
        "node_info": asdict(state.node_info),
        "result": asdict(state.result),
    }


def get_latest_run_id() -> str | None:
    if not LATEST_FILE.exists():
        return None
    data = _read_json(LATEST_FILE)
    return data.get("run_id")


def cmd_start(args: argparse.Namespace) -> None:
    result = start_analysis(args.query)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    run_id = args.run_id or get_latest_run_id()
    if not run_id:
        raise SystemExit("No run_id provided and no latest_run.json found.")
    result = query_status(run_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_wait(args: argparse.Namespace) -> None:
    run_id = args.run_id or get_latest_run_id()
    if not run_id:
        raise SystemExit("No run_id provided and no latest_run.json found.")

    deadline = time.time() + args.timeout
    while True:
        status = query_status(run_id)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        if status["status"] == "success":
            break
        if time.time() >= deadline:
            raise SystemExit(f"Timeout waiting for run {run_id}")
        time.sleep(args.interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Semi data analysis async mock runner")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start an analysis task")
    p_start.add_argument("--query", required=True, help="User raw natural language query")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="Query task status")
    p_status.add_argument("--run-id", help="Task run_id; defaults to latest")
    p_status.set_defaults(func=cmd_status)

    p_wait = sub.add_parser("wait", help="Poll until success")
    p_wait.add_argument("--run-id", help="Task run_id; defaults to latest")
    p_wait.add_argument("--interval", type=int, default=5, help="Poll interval in seconds")
    p_wait.add_argument("--timeout", type=int, default=1800, help="Timeout in seconds")
    p_wait.set_defaults(func=cmd_wait)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
