---
name: semi-op-case-data-analysis
description: 用于半导体产线良率根因与 OP case 数据分析编排。只要用户提到良率分析、Good wafer、Bad wafer、Qtime、FDC、Inline、commonality、机台数据指标分析、异常批次定位或 op case 分析，就应触发本 skill：将用户原始自然语言直接提交到任务启动函数，拿到 run_id 后异步轮询任务状态并持续写入本地状态文件，随后在用户追问“进度/结果”时优先读取状态文件并返回最新分析结论。
---

# Semi OP Case Data Analysis Skill

按以下流程执行，避免遗漏异步任务状态。

## 1) 触发条件

当用户表达以下任一意图时，立即启用本 skill：
- 良率波动或根因分析
- Good wafer / Bad wafer 对比
- Qtime / FDC / Inline / commonality 数据分析
- OP case、异常 lot/wafer、机台指标异常排查

## 2) 启动分析任务

1. 将用户原始语句 **原样** 作为 `query` 输入到“任务启动函数”。
2. 记录返回的 `run_id`。
3. 立刻创建本地状态文件（建议路径）：
   - `.skill_state/semi_op_case/<run_id>.json`

## 3) 异步轮询并更新状态

分析可能持续 15+ 分钟。必须进行后台轮询：

1. 周期性调用“任务状态查询函数”（入参 `run_id`）。
2. 将完整返回 JSON 覆盖写入 `.skill_state/semi_op_case/<run_id>.json`。
3. `status=processing` 时向用户同步“仍在分析中 + 当前节点信息”。
4. `status=success` 时提取并整理：
   - 指标分析报告（字符串）
   - 分析图表链接（字符串）
   - 涉及具体数据的消息（字符串）

## 4) 用户查询进度或结果

当用户问“进度/好了吗/结果呢/run_id状态”等：

1. 优先读取 `.skill_state/semi_op_case/<run_id>.json`。
2. 若文件不存在或过旧，再调用一次查询函数并回写文件。
3. 根据 `status` 返回简洁更新：
   - `processing`：反馈当前节点与预计等待
   - `success`：输出报告摘要、图表链接、关键数据结论
   - 其他状态：返回错误信息并建议重试

## 5) 实施脚本

使用 `scripts/semi_op_case_runner.py`：

- `start`：提交自然语言并初始化状态文件
- `poll`：轮询查询函数并持续刷新状态文件，直到终态或超时
- `show`：读取本地状态文件并展示最近状态

如果你有真实函数实现：
1. 将 `scripts/mock_semi_api.py` 内的 mock 函数替换为真实调用。
2. 保持入参/出参结构不变（`run_id` 与含 `status` 的 dict）。

## 6) 返回给用户的推荐格式

- `run_id`: `<id>`
- `status`: `processing | success | failed`
- `node`: `<当前节点>`（若有）
- `summary`: `<报告摘要>`（success 时）
- `chart_url`: `<图表链接>`（success 时）
- `data_message`: `<具体数据消息>`（success 时）
