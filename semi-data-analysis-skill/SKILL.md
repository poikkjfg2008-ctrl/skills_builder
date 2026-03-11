---
name: semi-data-analysis
description: 调用半导体产线数据分析函数，对良率异常与根因做指标分析。只要用户提到良率分析、Good wafer、Bad wafer、Qtime、FDC、Inline、commonality、机台传感器数据、产线根因定位、异常批次对比等语义，就应优先触发本 skill：将用户原始问题原样作为查询输入，启动异步分析并持续回查状态，拿到最终报告与图表链接后再回复。
---

# Semi Data Analysis Skill

## 目标
将用户的自然语言问题直接提交到“半导体产线指标分析”后端函数，获得：
1. 指标分析报告（字符串）
2. 图表展示链接（字符串）
3. 含具体数据的消息（字符串）

该流程是**异步长任务**（可能 15+ 分钟），因此需要 run_id + 状态轮询。

## 何时触发
当用户请求或语义涉及以下任意场景时触发：
- 良率分析、良率下滑、根因定位
- Good wafer / Bad wafer 对比
- Qtime / FDC / Inline / commonality 指标分析
- 机台传感器数据异常、批次异常、工站异常
- 产线数据驱动的异常归因或相关性排查

若用户明确要求“先查状态”“更新进度”“runid 结果怎么样”，也触发本 skill 的状态查询流程。

## 输入规则
- 将**用户原始语句**（不要改写、不要摘要）直接作为 `query` 输入分析函数。
- 若用户提供了 run_id，则直接查询该 run_id 的状态。

## 执行流程
按顺序执行：

1. **启动任务**
   - 调用 `start_analysis(query)`。
   - 记录返回的 `run_id`。
   - 将任务状态写入本地状态文件（见“状态文件约定”）。

2. **查询状态**
   - 调用 `query_status(run_id)` 获取最新状态。
   - 当 `status == "processing"`：
     - 告知用户任务仍在执行，并返回最近节点信息。
     - 更新状态文件。
   - 当 `status == "success"`：
     - 从结果中提取 report/chart/message。
     - 更新状态文件为完成。
     - 给用户返回最终分析结果。

3. **用户追问“进度/状态/结果”时**
   - 优先读取状态文件中最近 run_id。
   - 若找到未完成 run_id，继续查询。
   - 若无 run_id，提示用户提供 run_id 或重新发起分析。

## 状态文件约定
默认状态目录：`./runtime/semi_data_analysis/`
- 每个 run_id 一个文件：`{run_id}.json`
- 另维护索引文件：`latest_run.json`

### 单任务状态 JSON 结构（建议）
```json
{
  "run_id": "run_20260101_120102_abc123",
  "query": "最近三天CMP段Bad wafer飙升，帮我看FDC和Qtime是否有异常",
  "status": "processing",
  "node_info": {
    "current_node": "feature_aggregation",
    "progress": 0.45,
    "message": "正在聚合Inline与commonality特征"
  },
  "result": {
    "analysis_report": "",
    "chart_url": "",
    "data_message": ""
  },
  "updated_at": "2026-01-01T12:10:11Z"
}
```

## 回复模板

### A. 刚发起任务时
- 已启动半导体数据分析任务。
- run_id: `<RUN_ID>`
- 当前状态: `processing`
- 说明这是长任务，可稍后让我“查询 run_id 状态”。

### B. 处理中
- run_id: `<RUN_ID>`
- 状态: `processing`
- 当前节点: `<node_info.current_node>`
- 进度/信息: `<node_info.progress>` / `<node_info.message>`

### C. 完成
按以下三段输出：
1. **指标分析报告**：`<analysis_report>`
2. **图表链接**：`<chart_url>`
3. **关键数据消息**：`<data_message>`

## 实现建议（脚本）
参考 `scripts/semi_data_analysis_mock.py`：
- 内置了 mock 版本：
  - `start_analysis(query)`：立即返回 run_id，并写入 processing 状态。
  - `query_status(run_id)`：根据耗时从 processing 转为 success。
- 提供 CLI：
  - `start --query "..."`
  - `status --run-id "..."`
  - `wait --run-id "..." --interval 30 --timeout 1800`

当你接入真实函数时，仅需替换 mock 函数实现，保留状态文件协议与 CLI 不变。
