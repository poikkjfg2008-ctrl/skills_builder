"""Mock API functions for semiconductor OP case analysis.

Replace these functions with your real service calls while keeping signatures stable:
- start_analysis_job(query: str) -> str
- query_analysis_job(run_id: str) -> dict
"""

from __future__ import annotations

import json
import random
import time
import uuid
from pathlib import Path

_BACKEND_PATH = Path('.skill_state/semi_op_case/mock_backend_jobs.json')


def _load_jobs() -> dict:
    if not _BACKEND_PATH.exists():
        return {}
    return json.loads(_BACKEND_PATH.read_text(encoding='utf-8'))


def _save_jobs(jobs: dict) -> None:
    _BACKEND_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BACKEND_PATH.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding='utf-8')


def start_analysis_job(query: str) -> str:
    """Start a mock analysis job and return run_id."""
    jobs = _load_jobs()
    run_id = f"semi-{uuid.uuid4().hex[:12]}"
    jobs[run_id] = {
        'run_id': run_id,
        'query': query,
        'created_at': time.time(),
        'total_steps': random.randint(4, 8),
    }
    _save_jobs(jobs)
    return run_id


def query_analysis_job(run_id: str) -> dict:
    """Query mock analysis status by run_id."""
    jobs = _load_jobs()
    job = jobs.get(run_id)
    if job is None:
        return {'run_id': run_id, 'status': 'failed', 'error': 'run_id not found'}

    elapsed = time.time() - job['created_at']
    simulated_step = min(int(elapsed // 4) + 1, job['total_steps'])

    if simulated_step < job['total_steps']:
        return {
            'run_id': run_id,
            'status': 'processing',
            'node': f"step_{simulated_step}/{job['total_steps']}",
            'node_info': {
                'stage': 'feature_engineering' if simulated_step > 2 else 'data_ingestion',
                'progress': round(simulated_step / job['total_steps'], 2),
            },
            'meta': job,
        }

    return {
        'run_id': run_id,
        'status': 'success',
        'node': 'completed',
        'indicator_report': (
            'Qtime 在 EQP-12 夜班窗口出现尾部拉长；FDC 主轴振动 P95 偏离基线 +18%。'
            'Inline 显示 Metal-1 CD 偏移与 Bad wafer 显著相关，commonality 指向同 recipe 分支。'
        ),
        'chart_url': f'https://mock.semi.local/charts/{run_id}',
        'data_message': (
            '近24小时：Bad wafer 比例 2.1% -> 4.8%，集中在 LOT A17/A19；'
            '建议优先复核 EQP-12 维护记录与 recipe 参数回滚。'
        ),
        'meta': job,
    }
