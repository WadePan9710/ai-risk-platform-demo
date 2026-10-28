"""Structured risk tools exposed to the LangGraph agent."""

from __future__ import annotations

from typing import Any

from .demo_data import query_demo
from .kpi import build_kpi
from .knowledge import search as search_knowledge
from .platform_data import (
    build_audit,
    build_cases,
    build_features,
    build_lineage,
    build_models,
    build_strategy,
)


TOOL_SCHEMAS = [
    {
        "name": "portfolio_snapshot",
        "description": "Read portfolio-level decision, approval, first-overdue and dpd7 metrics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "due_from": {"type": "string", "description": "Optional YYYY-MM-DD"},
                "due_to": {"type": "string", "description": "Optional YYYY-MM-DD"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "cohort_comparison",
        "description": "Read EG/CG outcomes by final tier with sample sizes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "due_from": {"type": "string"},
                "due_to": {"type": "string"},
                "tier": {"type": "string", "enum": ["A", "B", "C", "D", "E", "F"]},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "rule_quality",
        "description": "Read rule-level first-overdue outcomes versus same-base-tier controls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "due_from": {"type": "string"},
                "due_to": {"type": "string"},
                "rule_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "model_health",
        "description": "Read AUC and sample status for registered risk models.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "strategy_snapshot",
        "description": "Read strategy versions, rules and current status.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "feature_catalog",
        "description": "Read feature inventory, quality metrics and feature-development jobs.",
        "input_schema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["online", "candidate"]}},
            "additionalProperties": False,
        },
    },
    {
        "name": "lineage_graph",
        "description": "Read source-to-feature-to-model-to-decision lineage edges.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "case_queue",
        "description": "Read risk cases, SLA and disposition status.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "audit_events",
        "description": "Read recent platform audit events.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "knowledge_search",
        "description": "Search approved company policy documents and return citations.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "disposition_queue",
        "description": "Read the current high-risk disposition queue.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


TOOL_METADATA = {
    "portfolio_snapshot": {"tier": "read", "owner": "risk analytics"},
    "cohort_comparison": {"tier": "read", "owner": "risk analytics"},
    "rule_quality": {"tier": "read", "owner": "strategy"},
    "model_health": {"tier": "read", "owner": "model risk"},
    "disposition_queue": {"tier": "read", "owner": "risk operations"},
    "strategy_snapshot": {"tier": "read", "owner": "strategy"},
    "feature_catalog": {"tier": "read", "owner": "data science"},
    "lineage_graph": {"tier": "read", "owner": "data governance"},
    "case_queue": {"tier": "read", "owner": "risk operations"},
    "audit_events": {"tier": "read", "owner": "governance"},
    "knowledge_search": {"tier": "read", "owner": "knowledge"},
}


def _kpi(due_from: str | None, due_to: str | None) -> dict[str, Any]:
    query = query_demo(due_from, due_to)
    return build_kpi(query["dataset"])


def _call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    run_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    due_from = arguments.get("due_from") or state.get("due_from")
    due_to = arguments.get("due_to") or state.get("due_to")
    call_id = f"tool_{run_id}_{len(state.get('tool_calls', [])) + 1}"

    if name == "portfolio_snapshot":
        kpi = _kpi(due_from, due_to)
        result = {
            "summary": kpi["summary"],
            "weekly_series": kpi["weekly_series"][-4:],
            "week_over_week": kpi["week_over_week"],
        }
    elif name == "cohort_comparison":
        kpi = _kpi(due_from, due_to)
        tier = arguments.get("tier")
        rows = kpi["tier_table"]
        result = {
            "rows": [row for row in rows if not tier or row["tier"] == tier],
            "power": kpi["power"],
        }
    elif name == "rule_quality":
        kpi = _kpi(due_from, due_to)
        rule_id = arguments.get("rule_id")
        rows = kpi["rule_quality"]["rows"]
        result = {
            "rows": [row for row in rows if not rule_id or row["rule_id"] == rule_id],
            "min_n": kpi["rule_quality"]["min_n"],
        }
    elif name == "model_health":
        kpi = _kpi(due_from, due_to)
        result = kpi["model_health"]
    elif name == "strategy_snapshot":
        result = build_strategy()
    elif name == "feature_catalog":
        query = query_demo(due_from, due_to)
        result = build_features(query["dataset"])
        status = arguments.get("status")
        if status:
            result = {**result, "rows": [row for row in result["rows"] if row["status"] == status]}
    elif name == "lineage_graph":
        result = build_lineage()
    elif name == "case_queue":
        query = query_demo(due_from, due_to)
        result = build_cases(query["dataset"])
    elif name == "audit_events":
        query = query_demo(due_from, due_to)
        result = build_audit(query["dataset"])
    elif name == "knowledge_search":
        query_text = str(arguments.get("query") or state.get("question") or "")
        rows = search_knowledge(query_text, limit=5)
        result = {
            "query": query_text,
            "rows": rows,
            "status": "done" if rows else "no_evidence",
        }
    elif name == "disposition_queue":
        kpi = _kpi(due_from, due_to)
        result = kpi["dispositions"]
    else:
        return {
            "call_id": call_id,
            "tool": name,
            "ok": False,
            "error": f"Unknown tool: {name}",
            "output": None,
        }

    return {
        "call_id": call_id,
        "tool": name,
        "ok": True,
        "input": arguments,
        "output": result,
        "tier": TOOL_METADATA[name]["tier"],
    }


def portfolio_snapshot(
    due_from: str | None = None,
    due_to: str | None = None,
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read portfolio KPI, weekend comparison and latest weekly cohorts."""
    return _call_tool(
        "portfolio_snapshot",
        {"due_from": due_from, "due_to": due_to},
        run_id=run_id,
        state=state or {},
    )


def cohort_comparison(
    due_from: str | None = None,
    due_to: str | None = None,
    tier: str | None = None,
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read EG/CG cohort comparison, optionally by final tier."""
    return _call_tool(
        "cohort_comparison",
        {"due_from": due_from, "due_to": due_to, "tier": tier},
        run_id=run_id,
        state=state or {},
    )


def rule_quality(
    due_from: str | None = None,
    due_to: str | None = None,
    rule_id: str | None = None,
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read rule precision versus a same-base-tier control group."""
    return _call_tool(
        "rule_quality",
        {"due_from": due_from, "due_to": due_to, "rule_id": rule_id},
        run_id=run_id,
        state=state or {},
    )


def model_health(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read model AUC health and freshness."""
    return _call_tool("model_health", {}, run_id=run_id, state=state or {})


def disposition_queue(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read the current disposition queue."""
    return _call_tool("disposition_queue", {}, run_id=run_id, state=state or {})


def strategy_snapshot(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read strategy versions and active rules."""
    return _call_tool("strategy_snapshot", {}, run_id=run_id, state=state or {})


def feature_catalog(
    status: str | None = None,
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read feature inventory and development jobs."""
    return _call_tool("feature_catalog", {"status": status}, run_id=run_id, state=state or {})


def lineage_graph(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read platform lineage nodes and edges."""
    return _call_tool("lineage_graph", {}, run_id=run_id, state=state or {})


def case_queue(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read risk cases and disposition state."""
    return _call_tool("case_queue", {}, run_id=run_id, state=state or {})


def audit_events(
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read recent governance audit events."""
    return _call_tool("audit_events", {}, run_id=run_id, state=state or {})


def knowledge_search(
    query: str,
    *,
    run_id: str = "manual",
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search approved knowledge and return citations."""
    return _call_tool("knowledge_search", {"query": query}, run_id=run_id, state=state or {})


TOOL_FUNCTIONS = {
    "portfolio_snapshot": portfolio_snapshot,
    "cohort_comparison": cohort_comparison,
    "rule_quality": rule_quality,
    "model_health": model_health,
    "disposition_queue": disposition_queue,
    "strategy_snapshot": strategy_snapshot,
    "feature_catalog": feature_catalog,
    "lineage_graph": lineage_graph,
    "case_queue": case_queue,
    "audit_events": audit_events,
    "knowledge_search": knowledge_search,
}
