---
name: semi-data-analysis
description: Semiconductor manufacturing yield root-cause analysis workflow for FDC/Qtime/Inline/commonality and Good wafer/Bad wafer scenarios. Use this skill whenever the user asks for 良率分析, root cause analysis, Good wafer, Bad wafer, Qtime, FDC, Inline, commonality, 机台/产线传感器数据指标分析, 异常批次排查, or status/result follow-up of a previously submitted analysis run.
---

# Semi Data Analysis Skill

Use this skill to call a long-running semiconductor data analysis function with the **user's original sentence** as input.

## Workflow

1. Keep the user sentence unchanged (no rewriting of domain terms).
2. Submit analysis job with the raw sentence.
3. Return `run_id` immediately and explain that analysis may take 15+ minutes.
4. Poll status by `run_id` until `status == success`, or return latest status when user asks for progress.
5. When completed, present:
   - 指标分析报告（字符串）
   - 图表链接（字符串）
   - 具体数据消息（字符串）

## Scripts in this skill

- `scripts/semi_analysis_runner.py`
  - `start`: submit a job, persist state JSON, return `run_id`
  - `status`: query one job status (`processing` / `success`)
  - `wait`: poll until success or timeout

## Command templates

```bash
python semi-data-analysis/scripts/semi_analysis_runner.py start \
  --query "<USER_ORIGINAL_TEXT>" \
  --state-dir .semi_skill_state
```

```bash
python semi-data-analysis/scripts/semi_analysis_runner.py status \
  --run-id "<RUN_ID>" \
  --state-dir .semi_skill_state
```

```bash
python semi-data-analysis/scripts/semi_analysis_runner.py wait \
  --run-id "<RUN_ID>" \
  --state-dir .semi_skill_state \
  --interval 20 \
  --timeout 1800
```

## Response pattern

- On submission: provide `run_id` and expected wait time.
- On progress query: read latest status JSON and summarize node progress.
- On completion: display report text, chart link, and detailed data message.

## Notes for production replacement

`semi_analysis_runner.py` currently includes **mock implementations** for:
- `run_semiconductor_analysis(query: str)`
- `query_analysis_status(run_id: str)`

Replace these with your real API/function calls while keeping the same I/O contract.
