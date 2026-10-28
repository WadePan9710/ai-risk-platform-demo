from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent_tools import cohort_comparison, model_health, portfolio_snapshot, rule_quality
from app.config import Settings
from app.graph import build_graph
from app.stats import two_proportion_z, wilson_interval


def test_stats_are_finite():
    result = two_proportion_z(20, 100, 10, 100)
    assert result is not None
    assert result["p"] < 0.1
    interval = wilson_interval(20, 100)
    assert interval is not None
    assert interval["low"] < 20 < interval["high"]


def test_synthetic_tools_return_real_denominators():
    state = {"run_id": "test"}
    portfolio = portfolio_snapshot(state=state)
    cohort = cohort_comparison(state=state)
    rules = rule_quality(state=state)
    models = model_health(state=state)
    assert portfolio["ok"] is True
    assert portfolio["output"]["summary"]["due1"] > 0
    assert cohort["output"]["power"]["pooled"]["eg_n"] > 0
    assert len(rules["output"]["rows"]) == 6
    assert len(models["output"]["models"]) >= 6


@pytest.mark.asyncio
async def test_graph_routes_and_narrates():
    graph = build_graph(InMemorySaver())
    settings = Settings(llm_api_key="", llm_base_url="", llm_model="")
    config = {"configurable": {"thread_id": "test-thread", "settings": settings}}
    await graph.ainvoke(
        {
            "run_id": "test-run",
            "question": "规则质量怎么样",
            "status": "running",
            "findings": [],
            "evidence": [],
            "tool_calls": [],
            "caveats": [],
        },
        config,
    )
    snapshot = await graph.aget_state(config)
    assert snapshot.values["route"] == "rules"
    assert snapshot.values["status"] == "done"
    assert snapshot.values["evidence"]
    assert snapshot.values["answer"]


@pytest.mark.asyncio
async def test_write_is_paused_and_only_executes_after_approval():
    graph = build_graph(InMemorySaver())
    settings = Settings(llm_api_key="", llm_base_url="", llm_model="")
    actions = []
    config = {"configurable": {"thread_id": "approval-thread", "settings": settings, "action_store": actions}}
    await graph.ainvoke(
        {
            "run_id": "approval-run",
            "question": "创建一个高风险处置工单",
            "status": "running",
            "findings": [],
            "evidence": [],
            "tool_calls": [],
            "caveats": [],
        },
        config,
    )
    snapshot = await graph.aget_state(config)
    assert snapshot.next
    assert not actions

    from langgraph.types import Command

    await graph.ainvoke(
        Command(resume={"decision": "approve", "note": "demo approval"}),
        config,
    )
    snapshot = await graph.aget_state(config)
    assert snapshot.values["status"] == "done"
    assert len(actions) == 1
    assert snapshot.values["final_action"]["executed"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "route", "tool"),
    [
        ("哪些特征 PSI 有风险", "features", "feature_catalog"),
        ("展示从数据源到决策的血缘", "lineage", "lineage_graph"),
        ("最近操作审计有哪些", "audit", "audit_events"),
        ("报销流程是什么", "knowledge", "knowledge_search"),
    ],
)
async def test_unified_graph_routes_to_platform_tools(question, route, tool):
    graph = build_graph(InMemorySaver())
    settings = Settings(llm_api_key="", llm_base_url="", llm_model="")
    config = {
        "configurable": {
            "thread_id": f"route-{route}",
            "settings": settings,
            "action_store": [],
        }
    }
    await graph.ainvoke(
        {
            "run_id": f"run-{route}",
            "question": question,
            "status": "running",
            "findings": [],
            "evidence": [],
            "tool_calls": [],
            "caveats": [],
        },
        config,
    )
    snapshot = await graph.aget_state(config)
    assert snapshot.values["route"] == route
    assert snapshot.values["tool_calls"][0]["tool"] == tool
