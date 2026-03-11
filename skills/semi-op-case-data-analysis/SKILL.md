---
name: semi-op-case-data-analysis
description: Analyze semiconductor fab yield/root-cause and operation case data using FDC, Qtime, Inline, and commonality signals through asynchronous tool calls. Use this skill whenever the user asks about 良率分析, root cause, Good wafer, Bad wafer, Qtime/FDC/Inline/commonality metrics, 机台数据指标分析, or op case analysis, especially when a long-running analysis job with run_id + status polling is required.
---

# Semi OP Case Data Analysis

Use this skill to translate user natural-language manufacturing questions into asynchronous data-analysis jobs.

## Execute workflow

1. Pass the **user's original utterance unchanged** into the analysis start function.
2. Receive a `run_id` from the start function.
3. Persist runtime state to a local JSON file so later turns can continue tracking progress.
4. Poll the status query function using `run_id` until completion (or timeout).
5. When `status == success`, summarize and present:
   - 指标分析报告 (string)
   - 分析图表链接 (string)
   - 涉及具体数据的消息 (string)

## Triggering heuristics

Always prioritize this skill when the request includes any of these intents:

- 良率异常、良率根因分析、制程波动
- Good wafer / Bad wafer 对比
- FDC/Qtime/Inline/commonality 指标趋势、异常检测、关联性分析
- OP case 分析、机台/产线数据归因

If the user asks to “查进度/看结果/状态更新”, read the saved run-state JSON and continue polling or return the latest known status.

## Runtime state contract

Store state files under `runtime/op_case_runs/`:

- `<run_id>.json`: latest status payload for that run
- `latest_run.json`: pointer to latest run and last query snapshot

Expected query payload shape:

```json
{
  "run_id": "...",
  "status": "processing | success | failed",
  "node": "optional current stage",
  "report": "指标分析报告字符串",
  "chart_url": "分析图表链接",
  "data_message": "涉及具体数据的消息字符串"
}
```

## Implementation note

Use `scripts/semi_op_case_runner.py` as the default orchestration helper.

- Replace `mock_start_analysis()` with your real task-start function.
- Replace `mock_query_status()` with your real run-status query function.

The script already includes:

- asynchronous polling loop
- timeout handling
- JSON state persistence for multi-turn continuation
- CLI for `start`, `query`, and `watch`
