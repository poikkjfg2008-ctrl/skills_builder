---
name: semi-data-analysis
description: Use this skill whenever users ask semiconductor yield/root-cause analysis using fab machine-line data, including mentions of 良率分析, Good wafer, Bad wafer, Qtime, FDC, Inline, commonality, 机台, 产线, wafer excursions, or indicator/metric diagnosis. The skill runs asynchronous semiconductor data analysis jobs from raw user natural language, tracks runid status, and returns report text + chart links + data message.
---

# Semi Data Analysis Skill

## Purpose

Use this skill to orchestrate semiconductor production-line data analysis via two backend functions:

1. `start_analysis(user_query: str) -> runid`
2. `query_status(runid: str) -> status_payload`

In this repo, these functions are **mocked** in `scripts/semi_data_analysis_runner.py` for integration reference. Replace the mock implementation with your real APIs later.

---

## When to trigger

Trigger this skill when the user asks anything about fab yield diagnosis or equipment/process metric analysis, for example:

- 良率分析 / root cause / 异常原因分析
- Good wafer / Bad wafer 对比
- Qtime, FDC, Inline, commonality 分析
- 机台/产线传感器指标分析
- Wafer map 异常归因 / lot 波动追因

If uncertain, prefer triggering this skill (under-triggering is worse than over-triggering for this workflow).

---

## Input

- Use the **user's original natural-language message** directly as analysis input.
- Do not rewrite into a rigid template unless user requests specific constraints.

---

## Execution model (asynchronous)

Analysis can take 15+ minutes. Use async polling:

1. Submit query and get `runid`.
2. Persist job state JSON in `semi-data-analysis/state/`.
3. Poll status periodically.
4. When status = `success`, return final outputs.

### Status semantics

- `processing`: still running.
- `success`: complete, final outputs available.
- `failed`: terminal failure.

---

## Agent workflow

### A) User asks for analysis

1. Call start function with raw user text.
2. Save/refresh local state file using `runid`.
3. Immediately reply with:
   - acknowledged execution started
   - `runid`
   - latest status summary
   - expected long runtime note
4. Continue polling (or poll on subsequent user request depending runtime policy).

### B) User asks “进度/状态/结果”

1. If user provides `runid`, use it.
2. Else read newest tracked run from `semi-data-analysis/state/`.
3. Call status query function.
4. Update state JSON.
5. Return concise status + node/progress info.

### C) When completed

Return all three business outputs clearly separated:

- `analysis_report` (text)
- `chart_url` (link)
- `data_message` (data-related message)

Also include short interpretation bullets for decision makers.

---

## Script usage (mock backend in this skill)

Script: `semi-data-analysis/scripts/semi_data_analysis_runner.py`

```bash
# Start a new analysis job
python semi-data-analysis/scripts/semi_data_analysis_runner.py start --query "请分析最近两周FDC和Qtime导致bad wafer上升的根因"

# Query a specific run
python semi-data-analysis/scripts/semi_data_analysis_runner.py status --runid <RUNID>

# Poll until completion (or timeout)
python semi-data-analysis/scripts/semi_data_analysis_runner.py wait --runid <RUNID> --interval 20 --timeout 1800
```

State files are written under:

- `semi-data-analysis/state/run_<RUNID>.json`
- `semi-data-analysis/state/latest_run.json`

---

## Output format guideline for end users

When reporting results to users, format as:

1. 运行状态（processing/success/failed）
2. runid
3. 节点进展（node info）
4. 若成功：
   - 指标分析报告
   - 图表链接
   - 关键数据消息
   - 下一步建议（可选）

---

## Integration note

To switch to production:

- Replace `mock_start_analysis()` with your real start API/function.
- Replace `mock_query_status()` with your real status API/function.
- Keep state persistence + polling orchestration unchanged for agent usability.
