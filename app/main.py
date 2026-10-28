from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from .agent_tools import TOOL_SCHEMAS
from .config import ROOT, Settings, get_settings
from .demo_data import query_demo
from .graph import build_graph
from .knowledge import knowledge_files, read_file
from .knowledge_agent import build_knowledge_graph
from .kpi import build_kpi
from .platform_data import (
    build_audit,
    build_cases,
    build_features,
    build_lineage,
    build_models,
    build_strategy,
    build_workspace_snapshot,
)


class AgentRunRequest(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    due_from: str | None = None
    due_to: str | None = None


class ApprovalRequest(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    note: str = Field(default="", max_length=300)


class KnowledgeQuery(BaseModel):
    question: str = Field(min_length=2, max_length=300)


def _thread_config(thread_id: str, settings: Settings, action_store: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "configurable": {
            "thread_id": thread_id,
            "settings": settings,
            "action_store": action_store if action_store is not None else app.state.action_store,
        }
    }


def _state_payload(values: dict[str, Any] | None) -> dict[str, Any]:
    state = values or {}
    return {
        "status": state.get("status", "running"),
        "route": state.get("route"),
        "routing_reason": state.get("routing_reason"),
        "answer": state.get("answer"),
        "findings": state.get("findings") or [],
        "evidence": state.get("evidence") or [],
        "tool_calls": state.get("tool_calls") or [],
        "caveats": state.get("caveats") or [],
        "final_action": state.get("final_action"),
        "model": state.get("model"),
        "model_calls": state.get("model_calls", 0),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(settings.checkpoint_path)) as checkpointer:
        app.state.settings = settings
        app.state.graph = build_graph(checkpointer)
        app.state.knowledge_graph = build_knowledge_graph(settings)
        app.state.action_store = []
        yield


app = FastAPI(title="RiskPilot Agent Demo", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "public"), name="static")


@app.get("/")
async def home():
    return FileResponse(ROOT / "public" / "index.html")


@app.get("/company-agent")
async def company_agent_page():
    return RedirectResponse(url="/#knowledge", status_code=307)


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(ROOT / "public" / "favicon.svg", media_type="image/svg+xml")


@app.get("/health")
async def health(request: Request):
    return {
        "ok": True,
        "service": "riskpilot-demo",
        "runtime": "python",
        "stack": ["fastapi", "langgraph", "langchain"],
        "models": TOOL_SCHEMAS,
    }


@app.get("/api/kpi")
async def kpi(
    due_from: str | None = Query(default=None),
    due_to: str | None = Query(default=None),
):
    query = query_demo(due_from, due_to)
    return build_kpi(query["dataset"])


@app.get("/api/workspace")
async def workspace(
    due_from: str | None = Query(default=None),
    due_to: str | None = Query(default=None),
):
    query = query_demo(due_from, due_to)
    return build_workspace_snapshot(query["dataset"])


@app.get("/api/platform/strategy")
async def strategy_snapshot():
    return build_strategy()


@app.get("/api/platform/models")
async def model_snapshot():
    return build_models(query_demo()["dataset"])


@app.get("/api/platform/features")
async def feature_snapshot():
    return build_features(query_demo()["dataset"])


@app.get("/api/platform/lineage")
async def lineage_snapshot():
    return build_lineage()


@app.get("/api/platform/cases")
async def case_snapshot():
    return build_cases(query_demo()["dataset"])


@app.get("/api/platform/audit")
async def audit_snapshot():
    return build_audit(query_demo()["dataset"])


@app.get("/api/meta")
async def meta():
    return {
        "name": "RiskPilot",
        "version": app.version,
        "tools": TOOL_SCHEMAS,
        "agent": {
            "framework": "LangGraph",
            "model_adapter": "LangChain",
            "api": "FastAPI",
            "checkpoint": "SQLite",
            "human_in_the_loop": True,
        },
    }


@app.post("/api/agent/runs")
async def start_agent_run(payload: AgentRunRequest, request: Request):
    settings: Settings = request.app.state.settings
    thread_id = f"thread_{uuid4().hex[:16]}"
    run_id = f"run_{uuid4().hex[:12]}"
    graph = request.app.state.graph
    config = _thread_config(thread_id, settings, request.app.state.action_store)
    initial = {
        "run_id": run_id,
        "question": payload.question,
        "due_from": payload.due_from,
        "due_to": payload.due_to,
        "status": "running",
        "findings": [],
        "evidence": [],
        "tool_calls": [],
        "caveats": [],
    }
    await graph.ainvoke(initial, config)
    snapshot = await graph.aget_state(config)
    state_payload = _state_payload(snapshot.values)
    return {
        "ok": True,
        "thread_id": thread_id,
        "run_id": run_id,
        "interrupted": bool(snapshot.next),
        "next": list(snapshot.next or []),
        "state": state_payload,
        "interrupt": (
            snapshot.tasks[0].interrupts[0].value
            if snapshot.tasks and snapshot.tasks[0].interrupts
            else None
        ),
    }


@app.get("/api/agent/runs/{thread_id}")
async def get_agent_run(thread_id: str, request: Request):
    snapshot = await request.app.state.graph.aget_state(
        _thread_config(thread_id, request.app.state.settings, request.app.state.action_store)
    )
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "ok": True,
        "thread_id": thread_id,
        "interrupted": bool(snapshot.next),
        "next": list(snapshot.next or []),
        "state": _state_payload(snapshot.values),
        "interrupt": (
            snapshot.tasks[0].interrupts[0].value
            if snapshot.tasks and snapshot.tasks[0].interrupts
            else None
        ),
    }


@app.post("/api/agent/runs/{thread_id}/resume")
async def resume_agent_run(thread_id: str, payload: ApprovalRequest, request: Request):
    graph = request.app.state.graph
    config = _thread_config(thread_id, request.app.state.settings, request.app.state.action_store)
    snapshot = await graph.aget_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="run not found")
    await graph.ainvoke(
        Command(
            resume={
                "decision": payload.decision,
                "note": payload.note,
            }
        ),
        config,
    )
    snapshot = await graph.aget_state(config)
    return {
        "ok": True,
        "thread_id": thread_id,
        "interrupted": bool(snapshot.next),
        "state": _state_payload(snapshot.values),
        "interrupt": (
            snapshot.tasks[0].interrupts[0].value
            if snapshot.tasks and snapshot.tasks[0].interrupts
            else None
        ),
    }


@app.get("/api/demo/contracts")
async def contracts():
    return {
        "source": "deterministic synthetic data",
        "freshness": "static for a reproducible portfolio demo",
        "no_llm_required": True,
        "fail_loudly": "Missing or insufficient denominators are returned as null with an explicit caveat.",
    }


@app.get("/api/knowledge/files")
async def knowledge_file_list():
    return {"ok": True, "files": knowledge_files()}


@app.get("/api/knowledge/files/{path:path}")
async def knowledge_file(path: str):
    return {"ok": True, "path": path, "content": read_file(path)}


@app.post("/api/knowledge/query")
async def knowledge_query(payload: KnowledgeQuery, request: Request):
    state = await request.app.state.knowledge_graph.ainvoke(
        {"question": payload.question}
    )
    return {
        "ok": True,
        "question": payload.question,
        **state,
    }
