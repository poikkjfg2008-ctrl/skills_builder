---
name: semi-data-analysis
description: Trigger this skill whenever the user asks about semiconductor yield analysis, good wafer vs bad wafer, FDC/Qtime/Inline/commonality metrics, station/tool/line sensor diagnostics, or root-cause analysis for production anomalies. Use this skill even if the user does not explicitly ask to "run a function"—if the intent is metric-based fab data analysis, invoke the async analysis workflow with the user’s original utterance as input.
---

# Semi Data Analysis Skill

## Purpose
Use fab data analysis functions to produce yield/root-cause insights from natural language requests.

This skill is designed for scenarios like:
- 良率根因分析 / 良率波动分析
- Good wafer / Bad wafer 对比
- Qtime / FDC / Inline / commonality 指标诊断
- 机台、产线、站点数据异常定位

## Input rule (strict)
When this skill is triggered, **pass the user's original request text directly** to the async submission function with no semantic rewriting.

## Output expectations
After the async workflow completes, present:
1. 指标分析报告（字符串）
2. 图表展示链接（字符串）
3. 涉及具体数据的消息（字符串）

## Async workflow
The analysis job may take 15+ minutes.

Use the helper script:
- `python scripts/run_semi_analysis.py start --query "<USER_ORIGINAL_MESSAGE>"`
  - Returns a `run_id` immediately.
- `python scripts/run_semi_analysis.py status --run-id <RUN_ID>`
  - Returns `status` and node info.
- `python scripts/run_semi_analysis.py wait --run-id <RUN_ID> --timeout 1200 --interval 20`
  - Polls until `success`, `failed`, or timeout.
- `python scripts/run_semi_analysis.py result --run-id <RUN_ID>`
  - Returns final report payload.

State is persisted to:
- `state/runs/<RUN_ID>.json`
- `state/last_run_id.txt`

This makes the workflow resumable when users later ask “结果怎么样了？” or “查一下 runid 状态”.

## Recommended assistant behavior
1. Detect trigger intent via keywords/context.
2. Submit with original user text.
3. Immediately tell user run_id and that processing is in progress.
4. On user follow-up, query status and continue polling.
5. On `success`, summarize key findings + provide report text/link/data message.

## Trigger cues
Strong trigger examples:
- “帮我看一下最近 bad wafer 的共性机台问题”
- “Qtime 变差导致良率下降吗？”
- “做一下 FDC 指标根因分析”
- “Inline 异常和最终良率有什么关系？”

Non-trigger examples:
- General semiconductor theory questions with no request to analyze factory data.
- Requests unrelated to metrics/sensor/wafer quality diagnostics.

## Notes
- The provided script uses **mock backend functions** so it can run end-to-end now.
- Replace mock implementations with your real production functions later.
