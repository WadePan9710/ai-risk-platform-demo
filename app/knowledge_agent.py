from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from .config import Settings
from .knowledge import search


class KnowledgeState(TypedDict, total=False):
    question: str
    status: str
    citations: list[dict[str, Any]]
    answer: str
    answer_mode: str
    restricted: bool


RESTRICTED_ACTIONS = ("发送", "导出", "提交", "外发", "邮件", "删除")
RESTRICTED_OBJECTS = ("客户数据", "个人信息", "客户", "数据文件", "外部")


def search_node(state: KnowledgeState) -> dict[str, Any]:
    results = search(state["question"], limit=6)
    if not results:
        return {
            "status": "no_evidence",
            "citations": [],
            "answer": "知识库没有找到足够依据。为避免编造，请补充问题或先补充知识文件。",
            "answer_mode": "deterministic",
        }
    top = results[0]
    restricted = any(word in state["question"] for word in RESTRICTED_ACTIONS) and any(
        word in state["question"] for word in RESTRICTED_OBJECTS
    )
    answer = (
        f"依据《{top['title']}》：{top['snippet']}"
        if not restricted
        else "该请求涉及对外转移或修改敏感数据，不能由 Agent 直接执行。需要数据负责人书面批准，并保留审批与审计记录。"
    )
    return {
        "status": "approval_required" if restricted else "done",
        "citations": results,
        "answer": answer,
        "answer_mode": "deterministic",
        "restricted": restricted,
    }


async def narrate_node(
    state: KnowledgeState,
    *,
    settings: Settings,
) -> dict[str, Any]:
    if not (settings.llm_api_key and settings.llm_base_url and settings.llm_model):
        return {"answer_mode": "deterministic"}
    if state.get("status") == "no_evidence":
        return {"answer_mode": "deterministic"}
    model = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0,
        timeout=60,
        max_retries=0,
    )
    try:
        message = await model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "Use only the supplied policy snippets. Write a concise Chinese answer. "
                        "Do not invent a rule or number. If the request is restricted, state that human approval is required."
                    )
                ),
                HumanMessage(
                    content=str(
                        {
                            "question": state["question"],
                            "answer": state.get("answer"),
                            "citations": [
                                {"title": item["title"], "snippet": item["snippet"]}
                                for item in state.get("citations", [])
                            ],
                            "restricted": state.get("restricted", False),
                        }
                    )
                ),
            ]
        )
        answer = str(message.content or "").strip() or state.get("answer") or ""
        return {"answer": answer, "answer_mode": "langchain"}
    except Exception:
        return {"answer_mode": "deterministic-fallback"}


def build_knowledge_graph(settings: Settings):
    async def run_narrator(state: KnowledgeState) -> dict[str, Any]:
        return await narrate_node(state, settings=settings)

    builder = StateGraph(KnowledgeState)
    builder.add_node("search", search_node)
    builder.add_node("narrate", run_narrator)
    builder.add_edge(START, "search")
    builder.add_edge("search", "narrate")
    builder.add_edge("narrate", END)
    return builder.compile()
