# Company Knowledge Copilot

> 该能力现在是 RiskPilot 统一工作台中的 Knowledge 模块，与策略、模型、特征、血缘、案件和审计共用同一个 LangGraph Agent。

## Problem

内部工作 Agent 需要回答政策、流程和口径问题，但不能靠模型记忆，也不能把公司资料直接暴露给未授权页面。

## Solution

知识模块将能力拆成四个边界：

1. **知识范围**：只读取 `demo_knowledge/` 下允许的 markdown。
2. **检索层**：章节化、关键词评分、片段提取、来源行号。
3. **回答层**：只基于命中的片段回答；无证据时显式拒答。
4. **动作层**：敏感外发或删除请求返回 `approval_required`，不直接执行。

## Graph

```text
START → knowledge_search → evidence_guard → grounded_answer → END
```

实际代码将检索和 guard 放在 `search_node` 中，保证没有检索结果时不会进入自由生成。

## Safety design

- `resolve()` 后验证目标仍在知识根目录内，阻止 `../` 路径越界。
- 搜索结果包含 `file / title / line / snippet / ref`。
- 前端只渲染检索结果和固定安全文案。
- Demo 知识文件是虚构内容，不包含真实公司资料。

## Interview talking points

- 为什么先做知识检索再做模型回答。
- 为什么引用是响应契约的一部分，而不是可选 UI。
- 如何用 `approval_required` 表示“可建议但不可直接执行”。
- 如何用路径规范化防止知识库读取越权。
