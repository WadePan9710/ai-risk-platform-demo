# Architecture

## Runtime

```text
Browser
  │
  ├─ GET /api/kpi
  │    └─ synthetic dataset → pure KPI functions
  │
  └─ POST /api/agent/runs
       └─ FastAPI
            └─ LangGraph StateGraph
                 ├─ route
                 ├─ evidence → LangChain tool contract
                 ├─ approval → interrupt / resume
                 ├─ execute_action
                 └─ narrator → optional LangChain ChatModel
```

## State

`AgentState` contains:

- `run_id`
- `question`
- `route`
- `evidence`
- `tool_calls`
- `findings`
- `caveats`
- `pending_action`
- `approval`
- `final_action`
- `answer`

LangGraph checkpoints use SQLite so a paused human-in-the-loop run can resume with the same `thread_id`.

## Trust boundaries

1. The browser can submit a question, not SQL or arbitrary tool code.
2. The router maps intent to a fixed tool allowlist.
3. The tool layer reads deterministic synthetic metrics.
4. The narrator receives structured findings only.
5. A write-like action pauses before execution and requires `Command(resume=...)`.

## Why LangGraph instead of a plain chat loop

- State transitions are explicit and testable.
- Tool calls and findings are inspectable.
- Human approval is a first-class graph state.
- SQLite checkpoints make the workflow resumable.
- A deterministic narrator keeps the demo usable without an API key.
