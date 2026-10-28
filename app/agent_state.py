from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


def merge_unique_strings(left: list[str] | None, right: list[str] | None) -> list[str]:
    return list(dict.fromkeys([*(left or []), *(right or [])]))


def merge_unique_refs(left: list[dict[str, Any]] | None, right: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rows = {item.get("ref") or str(item): item for item in [*(left or []), *(right or [])]}
    return list(rows.values())


class AgentState(TypedDict, total=False):
    run_id: str
    question: str
    due_from: str | None
    due_to: str | None
    route: Literal[
        "portfolio", "strategy", "experiment", "rules", "models",
        "features", "lineage", "cases", "audit", "knowledge", "clarify",
    ]
    routing_reason: str
    evidence: Annotated[list[dict[str, Any]], merge_unique_refs]
    findings: Annotated[list[dict[str, Any]], operator.add]
    tool_calls: Annotated[list[dict[str, Any]], operator.add]
    caveats: Annotated[list[str], merge_unique_strings]
    pending_action: dict[str, Any] | None
    approval: dict[str, Any] | None
    final_action: dict[str, Any] | None
    answer: str
    status: str
    model: str
    model_calls: int
