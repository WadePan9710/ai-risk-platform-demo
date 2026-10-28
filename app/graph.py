from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agent_state import AgentState
from .agent_tools import TOOL_FUNCTIONS
from .config import Settings
from .narrator import narrate


ROUTE_KEYWORDS = {
    "portfolio": ["组合", "整体", "通过率", "放款", "首逾", "趋势", "本周"],
    "strategy": ["策略", "阈值", "版本", "仿真", "降档", "额度规则"],
    "experiment": ["eg", "cg", "实验", "对照", "分档", "功效", "显著"],
    "rules": ["规则", "命中", "陪跑", "精准", "降档", "阈值"],
    "models": ["模型", "auc", "ks", "衰减", "随机", "体检"],
    "features": ["特征", "变量", "iv", "ks", "psi", "开发", "候选", "缺失"],
    "lineage": ["血缘", "来源", "上游", "字段", "链路", "数据源"],
    "cases": ["处置", "工单", "名单", "人工", "队列", "高风险", "案件"],
    "audit": ["审计", "操作记录", "谁改", "合规", "trace"],
    "knowledge": ["知识库", "政策", "流程", "报销", "制度", "口径文档"],
}


def route_question(question: str) -> tuple[str, str]:
    text = question.lower()
    scores = {
        route: sum(1 for keyword in keywords if keyword in text)
        for route, keywords in ROUTE_KEYWORDS.items()
    }
    route, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return "clarify", "没有识别到风险分析意图"
    return route, f"关键词命中 {score} 个"


def route_node(state: AgentState) -> dict[str, Any]:
    route, reason = route_question(state.get("question", ""))
    if route == "clarify":
        return {
            "route": "clarify",
            "routing_reason": reason,
            "status": "clarify",
            "answer": "请说明你想看组合风险、策略、实验、规则、模型、特征、血缘、案件、审计还是知识库。",
        }
    text = state.get("question", "")
    write_intent = route == "cases" and any(
        phrase in text for phrase in ("创建", "加入", "转人工", "登记", "派单")
    )
    pending = (
        {
            "type": "create_case",
            "title": "创建高风险处置案件",
            "risk": "medium",
            "reason": "Agent 识别到处置请求，执行前必须人工确认。",
        }
        if write_intent
        else None
    )
    return {
        "route": route,
        "routing_reason": reason,
        "status": "running",
        "pending_action": pending,
    }


def route_next(state: AgentState) -> str:
    return "clarify" if state.get("route") == "clarify" else "evidence"


def evidence_node(state: AgentState) -> dict[str, Any]:
    route = state.get("route")
    tool = {
        "portfolio": "portfolio_snapshot",
        "strategy": "strategy_snapshot",
        "experiment": "cohort_comparison",
        "rules": "rule_quality",
        "models": "model_health",
        "features": "feature_catalog",
        "lineage": "lineage_graph",
        "cases": "case_queue",
        "audit": "audit_events",
        "knowledge": "knowledge_search",
    }.get(route, "portfolio_snapshot")
    fn = TOOL_FUNCTIONS[tool]
    kwargs: dict[str, Any] = {"run_id": state["run_id"], "state": state}
    if tool in ("portfolio_snapshot", "cohort_comparison", "rule_quality"):
        kwargs.update(due_from=state.get("due_from"), due_to=state.get("due_to"))
    if tool == "knowledge_search":
        kwargs.update(query=state["question"])
    result = fn(**kwargs)
    findings: list[dict[str, Any]] = []
    output = result.get("output") or {}
    if tool == "portfolio_snapshot":
        summary = output.get("summary") or {}
        wow = output.get("week_over_week") or {}
        findings = [
            {"label": "首期 dpd1+", "value": summary.get("first_overdue_rate"), "unit": "%"},
            {"label": "可判样本", "value": summary.get("due1"), "unit": " 笔"},
            {"label": "放款单数", "value": summary.get("loans"), "unit": " 单"},
            {
                "label": "最近完整周环比",
                "value": wow.get("diff_pp"),
                "unit": f"pp · {wow.get('direction')}" if wow.get("available") else "pp",
            },
        ]
    elif tool == "cohort_comparison":
        power = output.get("power") or {}
        pooled = power.get("pooled") or {}
        eg_n = pooled.get("eg_n") or 0
        cg_n = pooled.get("cg_n") or 0
        findings = [
            {"label": "可检验分档", "value": power.get("testable"), "unit": "/6"},
            {"label": "显著分档", "value": power.get("significant"), "unit": "/6"},
            {"label": "EG 合并首逾", "value": round(pooled.get("eg_num", 0) / eg_n * 100, 1) if eg_n else None, "unit": f"% ({pooled.get('eg_num', 0)}/{eg_n})"},
            {"label": "CG 合并首逾", "value": round(pooled.get("cg_num", 0) / cg_n * 100, 1) if cg_n else None, "unit": f"% ({pooled.get('cg_num', 0)}/{cg_n})"},
        ]
    elif tool == "rule_quality":
        rows = output.get("rows", [])
        findings = [
            {"label": "精准规则", "value": sum(1 for row in rows if row.get("verdict") == "精准"), "unit": " 条"},
            {"label": "陪跑规则", "value": sum(1 for row in rows if row.get("verdict") == "陪跑"), "unit": " 条"},
            {"label": "待复核规则", "value": sum(1 for row in rows if row.get("verdict") == "待复核"), "unit": " 条"},
            {
                "label": "最高区分度规则",
                "value": max(rows, key=lambda row: row.get("delta_pp") or -999)["label"] if rows else None,
                "unit": "",
            },
        ]
    elif tool == "model_health":
        models = output.get("models") or []
        findings = [
            {"label": "模型总数", "value": len(output.get("models") or []), "unit": " 个"},
            {"label": "接近随机", "value": sum(1 for m in output.get("models", []) if m.get("verdict") == "接近随机"), "unit": " 个"},
            {
                "label": "需关注模型",
                "value": "、".join(m["name"] for m in models if m.get("verdict") in ("接近随机", "衰减")),
                "unit": "",
            },
        ]
    elif tool == "strategy_snapshot":
        strategies = output.get("strategies") or []
        findings = [
            {"label": "策略总数", "value": len(strategies), "unit": " 个"},
            {"label": "线上策略", "value": sum(1 for row in strategies if row["status"] == "online"), "unit": " 个"},
            {"label": "草稿策略", "value": sum(1 for row in strategies if row["status"] == "draft"), "unit": " 个"},
        ]
    elif tool == "feature_catalog":
        summary = output.get("summary") or {}
        findings = [
            {"label": "特征总数", "value": summary.get("total"), "unit": " 个"},
            {"label": "生产特征", "value": summary.get("online"), "unit": " 个"},
            {"label": "候选特征", "value": summary.get("candidate"), "unit": " 个"},
            {"label": "高 PSI 告警", "value": summary.get("high_psi"), "unit": " 个"},
        ]
    elif tool == "lineage_graph":
        summary = output.get("summary") or {}
        findings = [
            {"label": "血缘节点", "value": summary.get("nodes"), "unit": " 个"},
            {"label": "血缘边", "value": summary.get("edges"), "unit": " 条"},
            {"label": "数据源", "value": summary.get("sources"), "unit": " 个"},
        ]
    elif tool == "case_queue":
        summary = output.get("summary") or {}
        findings = [
            {"label": "案件总数", "value": summary.get("total"), "unit": " 件"},
            {"label": "待处置", "value": summary.get("open"), "unit": " 件"},
            {"label": "高风险", "value": summary.get("high"), "unit": " 件"},
        ]
    elif tool == "audit_events":
        summary = output.get("summary") or {}
        findings = [
            {"label": "审计事件", "value": summary.get("events"), "unit": " 条"},
            {"label": "涉及主体", "value": summary.get("actors"), "unit": " 个"},
            {"label": "待确认", "value": summary.get("pending"), "unit": " 条"},
        ]
    elif tool == "knowledge_search":
        rows = output.get("rows") or []
        findings = [
            {"label": "命中政策章节", "value": len(rows), "unit": " 个"},
            {"label": "首条来源", "value": rows[0]["ref"] if rows else None, "unit": ""},
        ]
        if not rows:
            return {
                "status": "no_evidence",
                "evidence": [],
                "tool_calls": [result],
                "findings": findings,
                "caveats": ["知识库没有找到可引用依据，因此拒答。"],
            }
    ref = {"ref": result.get("call_id"), "tool": tool, "why": "Agent evidence read"}
    evidence = [ref]
    if tool == "knowledge_search":
        evidence.extend(
            {"ref": row["ref"], "tool": "knowledge", "why": row["title"]}
            for row in (output.get("rows") or [])
        )
    return {
        "evidence": evidence,
        "tool_calls": [result],
        "findings": findings,
        "caveats": ["演示数据为确定性合成数据；真实生产版应由只读数据网关提供证据。"],
    }


def approval_node(state: AgentState) -> dict[str, Any]:
    # Only a write action stops here. The current read-only demo uses this branch
    # to demonstrate LangGraph human-in-the-loop, not to mutate data.
    pending = state.get("pending_action") or {}
    decision = interrupt(
        {
            "type": "approval",
            "run_id": state["run_id"],
            "action": pending,
            "reason": "写入动作必须由人工批准。",
        }
    )
    return {"approval": decision}


def finish_node(state: AgentState) -> dict[str, Any]:
    return {
        "status": "done",
        "final_action": state.get("final_action")
        or {"type": "read_only", "executed": False},
    }


def execute_action_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    approval = state.get("approval") or {}
    pending = state.get("pending_action") or {}
    if approval.get("decision") != "approve":
        return {
            "status": "rejected",
            "final_action": {
                "type": "action_rejected",
                "executed": False,
                "action": pending,
            },
        }
    store: list[dict[str, Any]] = config["configurable"]["action_store"]
    row = {
        "id": f"DP-{len(store) + 1:04d}",
        "run_id": state["run_id"],
        "action": pending,
        "status": "open",
        "approved_by": "demo-user",
    }
    store.append(row)
    return {
        "status": "done",
        "final_action": {
            "type": "action_executed",
            "executed": True,
            "action": pending,
            "record": row,
        },
    }


def after_evidence(state: AgentState) -> str:
    return "approval" if state.get("pending_action") else "finish"


def after_approval(state: AgentState) -> str:
    return "execute_action"


async def narrate_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    settings: Settings = config["configurable"]["settings"]
    result = await narrate(state, settings)
    return result


def build_graph(checkpointer: Any):
    builder = StateGraph(AgentState)
    builder.add_node("route", route_node)
    builder.add_node("evidence", evidence_node)
    builder.add_node("approval", approval_node)
    builder.add_node("execute_action", execute_action_node)
    builder.add_node("finish", finish_node)
    builder.add_node("narrate", narrate_node)
    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        route_next,
        {"clarify": END, "evidence": "evidence"},
    )
    builder.add_conditional_edges(
        "evidence",
        after_evidence,
        {"approval": "approval", "finish": "finish"},
    )
    builder.add_conditional_edges(
        "approval",
        after_approval,
        {"execute_action": "execute_action"},
    )
    builder.add_edge("execute_action", "narrate")
    builder.add_edge("finish", "narrate")
    builder.add_edge("narrate", END)
    return builder.compile(checkpointer=checkpointer)
