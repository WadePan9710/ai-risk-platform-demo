# 简历项目描述

## 项目标题

RiskPilot · FastAPI + LangGraph + LangChain 风控策略 Agent

## 简历 Bullet

- 设计并实现 FastAPI + LangGraph + LangChain 统一风控 Agent 工作台，覆盖组合风险、策略、模型、特征开发、变量血缘、案件处置、知识库与审计。
- 使用 LangGraph `interrupt()` 与 SQLite checkpoint 实现 Human-in-the-Loop，写动作在人工批准前保持暂停，批准后通过命令恢复并落执行状态。
- 将 KPI 计算与 LLM 表达解耦，模型只读取结构化 findings，平台在无 API Key 时仍可运行确定性 narrator。
- 实现 EG/CG 分档两比例 z 检验、首期 dpd1+ 周趋势、成熟度门控和规则质量对照组，所有率值同时返回分子与分母。
- 设计特征目录、IV/KS/PSI 质量检查、特征开发任务和“数据源→特征→指标→模型/策略→决策”血缘视图，并全部纳入统一 Agent 工具路由。
- 实现知识库章节检索、来源行号、路径越界防护、无证据拒答和敏感请求 `approval_required`，与业务模块共用同一 Agent。
- 使用 FastAPI 单进程托管 API 与响应式工作台，提供 Agent Trace、工具 `call_id`、证据链和审批交互，自动化测试覆盖跨模块路由、统计与中断恢复。

## 面试一句话

我把一个传统的风控 KPI Demo 重构成完整 Agent 工作台：确定性模块负责事实，LangGraph 负责跨域流程和安全边界，LangChain 只负责表达。
