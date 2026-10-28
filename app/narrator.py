from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import Settings


def deterministic_answer(state: dict[str, Any]) -> str:
    findings = state.get("findings") or []
    caveats = state.get("caveats") or []
    parts = []
    for item in findings[:4]:
        value = item.get("value")
        parts.append(f"{item.get('label')}：{value}{item.get('unit') or ''}")
    if not parts:
        return "当前问题没有足够可判定的数据，请补充时间窗或分析对象。"
    prefix = {
        "portfolio": "组合风险脉络显示",
        "strategy": "策略运行态显示",
        "experiment": "实验分层结果显示",
        "rules": "规则质量校验显示",
        "models": "模型体检结果显示",
        "features": "特征资产显示",
        "lineage": "血缘审计显示",
        "cases": "案件队列显示",
        "audit": "审计轨迹显示",
        "knowledge": "知识依据显示",
    }.get(state.get("route"), "分析结果显示")
    final_action = state.get("final_action") or {}
    action_text = ""
    if final_action.get("type") == "action_rejected":
        action_text = " 处置动作已被人工拒绝，未写任何记录。"
    elif final_action.get("type") == "action_executed":
        action_text = f" 处置动作已获批准并执行，记录号 {final_action.get('record', {}).get('id')}。"
    text = f"{prefix}，" + "；".join(parts) + "。" + action_text
    if caveats:
        text += f" 注意：{caveats[0]}"
    return text


async def narrate(state: dict[str, Any], settings: Settings) -> dict[str, Any]:
    fallback = deterministic_answer(state)
    if not (settings.llm_api_key and settings.llm_base_url and settings.llm_model):
        return {
            "answer": fallback,
            "model": "deterministic-narrator",
            "model_calls": 0,
        }

    model = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        timeout=60,
        max_retries=0,
    )
    try:
        message = await model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "You are a risk strategy analyst. Use only the supplied findings and numbers. "
                        "Write a concise Chinese answer for a portfolio demo. Do not invent values. "
                        "State uncertainty explicitly."
                    )
                ),
                HumanMessage(content=str({"route": state.get("route"), "findings": state.get("findings"), "caveats": state.get("caveats")})),
            ]
        )
        text = str(message.content or "").strip() or fallback
        return {"answer": text, "model": settings.llm_model, "model_calls": 1}
    except Exception as exc:
        return {
            "answer": fallback,
            "model": f"deterministic-fallback: {str(exc)[:80]}",
            "model_calls": 1,
        }
