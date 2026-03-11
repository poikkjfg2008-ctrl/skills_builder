---
name: semi-op-case-data-analysis
description: 用于半导体产线良率根因与 OP Case 数据分析。只要用户提到良率分析、Good wafer、Bad wafer、Qtime、FDC、Inline、commonality、机台指标、产线异常归因、OP case 分析等场景，就应优先触发该技能。该技能会把用户原始自然语言直接提交到分析任务启动函数，拿到 run_id 后持续查询状态，完成后返回指标分析报告、图表链接与关键数据消息。
---

# Semi OP Case Data Analysis Skill

## 目标
将用户的自然语言问题直接提交给产线数据分析系统（FDC/Qtime/Inline/commonality），并通过 `run_id` 进行异步轮询，直到可返回完整分析结果。

## 触发条件（强触发）
当用户请求中出现以下任一内容时，应直接使用本技能：
- 良率分析、良率下降、根因分析
- Good wafer / Bad wafer
- Qtime / FDC / Inline / commonality
- 机台数据指标分析、OP case 分析
- 需要“分析报告 + 图表链接 + 数据消息”的产线诊断

如果用户只是泛泛聊天且没有分析意图，可不触发。

## 输入约束
- **必须使用用户原始语句** 作为启动函数入参，不改写、不裁剪业务信息。
- 如果用户一次给了多条独立分析请求，建议拆成多个 run。

## 执行流程
1. 调用“任务启动函数”并传入用户原始语句。
2. 获得 `run_id` 后，立即告知用户任务已启动。
3. 进入异步查询：用 `run_id` 轮询“任务状态查询函数”。
4. 每次查询结果都落盘到本地状态文件，便于后续“继续查进度/补拿结果”。
5. 当 `status=success`，提取并返回：
   - 指标分析报告（字符串）
   - 分析图表链接（字符串）
   - 涉及具体数据的消息（字符串）

## 轮询与状态持久化约定
- 建议状态目录：`state/`
- 文件命名：`state/<run_id>.json`
- 可选最新任务指针：`state/latest_run_id.txt`
- 轮询间隔建议：20~60 秒（长任务最高可超过 15 分钟）

## 用户沟通模板
- 启动后：
  - “已提交 OP case 分析任务，run_id=<id>。我会持续查询进度并在完成后返回报告与图表链接。”
- 处理中：
  - “任务仍在执行中（status=processing），当前节点：<node/message>。”
- 成功后：
  - “分析已完成。以下是报告、图表链接和关键数据结论。”

## 异常处理
- `run_id` 不存在/失效：提示用户重试提交。
- 轮询超时：返回当前最新状态与已知节点信息，并询问是否继续后台跟踪。
- 返回字段缺失：如实告知缺失项，同时返回已有结果。

## 脚本入口（mock，可替换真实函数）
本 skill 附带 `scripts/semi_op_case_runner.py`，包含：
- `start_analysis_task(user_query)`：启动任务，返回 `run_id`
- `query_analysis_status(run_id)`：查询状态，返回含 `status` 的字典
- `watch_run(...)`：轮询并持久化状态

当你接入真实环境时，只需替换上述两个函数内部实现，其余轮询与落盘逻辑可复用。
