---
name: semi-op-case-data-analysis
description: 用于半导体产线良率/根因分析的技能。只要用户提到良率分析、Good wafer、Bad wafer、Qtime、FDC、Inline、commonality、机台数据指标分析、op case 分析等，就应触发本技能。将用户原始自然语言原样传给分析任务启动函数，拿到 run_id 后持续查询状态并在完成后返回指标分析报告、图表链接和数据消息。
---

# Semi OP Case Data Analysis

用于把用户的自然语言问题转成一次可追踪的半导体产线数据分析任务，并在异步执行期间维护状态。

## 何时必须使用

当用户请求或明显暗示以下内容时，必须优先使用此技能：

- 良率分析 / root cause / 根因定位
- Good wafer / Bad wafer 对比
- Qtime / FDC / Inline / commonality 数据分析
- OP case 分析 / 机台数据指标分析

## 输入输出约定

- 输入：用户原始自然语言字符串（不要改写，不要摘要）。
- 任务启动函数输出：`run_id`。
- 状态查询函数输入：`run_id`。
- 状态查询输出：`dict`，至少包含 `status` 字段：
  - `processing`：仍在执行
  - `success`：执行完成，返回：
    - `metric_report`（字符串）
    - `chart_link`（字符串）
    - `data_message`（字符串）

## 操作流程（Agent）

1. **直接转发原始用户语句**到启动函数，获得 `run_id`。
2. 立即告知用户任务已启动，并回传 `run_id`。
3. 进入轮询：每 20~60 秒查询一次状态函数。
4. 每次查询结果写入本地状态文件：`./runtime/op_case_runs/<run_id>.json`。
5. 若 `status=processing`：
   - 给用户简短进度更新（可包含阶段/节点信息）。
6. 若 `status=success`：
   - 输出 `metric_report`、`chart_link`、`data_message`。
   - 标记该 run 完成并停止轮询。

## 异步与持久化约定

- 状态文件根目录：`./runtime/op_case_runs/`
- 每个任务一个文件：`<run_id>.json`
- 文件建议结构：

```json
{
  "run_id": "run_20260101_abcdef",
  "created_at": "2026-01-01T10:00:00Z",
  "updated_at": "2026-01-01T10:05:00Z",
  "latest": {
    "status": "processing",
    "node": "inline_feature_join",
    "progress": 0.42
  },
  "history": [
    {"ts": "2026-01-01T10:00:00Z", "status": "processing"},
    {"ts": "2026-01-01T10:05:00Z", "status": "processing", "node": "inline_feature_join"}
  ]
}
```

## 使用脚本

优先使用脚本而不是手写重复逻辑：

- 启动任务：
  - `python semi-op-case-data-analysis/scripts/op_case_runtime.py start --query "<用户原句>"`
- 查询状态并更新状态文件：
  - `python semi-op-case-data-analysis/scripts/op_case_runtime.py poll --run-id <run_id>`
- 启动并持续等待直到完成（演示/调试）：
  - `python semi-op-case-data-analysis/scripts/op_case_runtime.py watch --query "<用户原句>" --interval 30`

## 函数对接说明（你替换真实函数时看这里）

`scripts/op_case_runtime.py` 中包含两个 mock 函数：

- `start_analysis_task(user_query: str) -> str`
- `query_analysis_status(run_id: str) -> dict`

你只需要保留函数签名并替换实现为真实服务调用，即可复用本技能流程。
