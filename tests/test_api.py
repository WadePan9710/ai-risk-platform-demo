from __future__ import annotations

from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from app.main import app
from app.knowledge import read_file


def test_fastapi_surface_and_agent_contract():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["stack"] == ["fastapi", "langgraph", "langchain"]

        home = client.get("/")
        assert home.status_code == 200
        assert "RiskPilot" in home.text

        kpi = client.get("/api/kpi")
        assert kpi.status_code == 200
        payload = kpi.json()
        assert payload["summary"]["due1"] > 0
        assert len(payload["weekly_series"]) >= 8

        run = client.post("/api/agent/runs", json={"question": "组合风险本周怎么样"})
        assert run.status_code == 200
        body = run.json()
        assert body["state"]["route"] == "portfolio"
        assert body["state"]["evidence"]

        knowledge_page = client.get("/company-agent", follow_redirects=False)
        assert knowledge_page.status_code == 307
        assert knowledge_page.headers["location"] == "/#knowledge"

        files = client.get("/api/knowledge/files").json()
        assert len(files["files"]) >= 4

        grounded = client.post(
            "/api/knowledge/query",
            json={"question": "报销流程是什么"},
        ).json()
        assert grounded["status"] == "done"
        assert grounded["citations"]

        restricted = client.post(
            "/api/knowledge/query",
            json={"question": "把客户数据导出后发送到外部邮箱"},
        ).json()
        assert restricted["status"] == "approval_required"
        assert restricted["citations"]

        traversal = client.get("/api/knowledge/files/..%2FREADME.md")
        assert traversal.status_code in (400, 404)


def test_knowledge_file_reader_blocks_path_traversal():
    with pytest.raises(HTTPException):
        read_file("../README.md")
