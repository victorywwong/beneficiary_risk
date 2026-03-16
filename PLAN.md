# Implementation Plan: Multi-Agent Beneficiary Risk System

## Status Legend
- ✅ Done
- 🔧 Done but needs polish
- ⬜ Not started

---

## Step 1 — Project Scaffolding & Config ✅
- `requirements.txt`, `config.py`, `.env.example`, `.gitignore`

## Step 2 — Schemas / Contracts ✅
- `schemas/payment.py` — `Payment`, `Sender`, `Recipient`
- `schemas/agent_result.py` — `AgentResult`, `RiskSignal`
- `schemas/orchestrator_plan.py` — `OrchestratorPlan`, `AgentType`
- `schemas/risk_decision.py` — `RiskDecision`, `Decision`

## Step 3 — Knowledge Base ✅
- `knowledge/schema.sql` — 4 tables: company_registry, adverse_media, payment_history, sanctions_pep
- `knowledge/seed.py` — 5 recipients with varied risk profiles
- `knowledge/database.py` — scoped query functions (information boundary enforcement)

## Step 4 — LLM Client ✅
- `llm/client.py` — `AsyncOpenAI` → OpenRouter, supports `tools` + `response_format`
- 🔧 Debug `print` statements still in client — replace with structlog

## Step 5 — Base Agent ✅
- `agents/base.py` — agentic tool-use loop (DB lookups) + `response_format` for structured output
- Timeout → unavailable AgentResult
- `MAX_TOOL_ITERATIONS = 5` guard

## Step 6 — Specialist Agents ✅
- `agents/company_agent.py` — `GET_COMPANY_DATA_TOOL`
- `agents/adverse_media_agent.py` — `GET_ADVERSE_MEDIA_TOOL`
- `agents/payment_pattern_agent.py` — `GET_PAYMENT_HISTORY_TOOL`
- `agents/sanctions_agent.py` — `GET_SANCTIONS_DATA_TOOL`
- Each agent: scoped DB tool + `_execute_db_tool` dispatch

## Step 7 — Temporal Workflow & Activities ✅
- `docker-compose.yml` — Temporal + PostgreSQL + Web UI
- `workflows/investigate.py` — parallel fan-out, sanctions guardrail, exception handling
- `activities/planner.py` — LLM planner with tool use, fallback to all agents
- `activities/company.py`, `adverse_media.py`, `payment_pattern.py`, `sanctions.py`
- `worker.py`, `main.py`

## Step 8 — Synthesizer ✅
- `orchestrator/synthesizer.py` — deterministic, no LLM
- Hard rules: sanctions HIGH → REJECT, sanctions unavailable → REVIEW
- Weighted scoring: sanctions 0.4, company 0.25, adverse_media 0.25, payment_pattern 0.1

## Step 9 — Observability 🔧
- `observability/logging.py` — structlog JSON with trace context
- 🔧 `llm/client.py` debug prints should use structlog (log model, endpoint, tool names per call)
- ⬜ Log token usage from OpenRouter responses

## Step 10 — Entry Points ✅
- `main.py` — `--payment-file` CLI, submits workflow, prints JSON result
- `worker.py` — Temporal worker

## Step 11 — Tests ✅
- `tests/test_synthesizer.py` — 6 unit tests (all hard rules + weighted scoring)
- `tests/test_agents.py` — 3 unit tests (tool loop, timeout, exception)
- `tests/test_workflow.py` — 4 integration tests via `TestWorkflowEnvironment`
- All 13 tests passing
- ⬜ Integration test: real DB seed + mocked LLM, verifies SQL → tool result → LLM loop

## Step 12 — Evaluation Harness ⬜
- `eval/harness.py` exists — runs labeled payments N times, reports accuracy + consistency
- ⬜ Run end-to-end against live Temporal + real LLM
- ⬜ Add more labeled payments (currently only 2: safe + sanctioned)
- ⬜ Per-agent availability rate reporting

## Step 13 — README 🔧
- `README.md` exists with setup instructions and architecture overview
- 🔧 Update to reflect tool-use architecture (no longer pre-fetches context)
- 🔧 Add example of actual output from smoke test

---

## Remaining Work (Priority Order)

| # | Task | File(s) |
|---|---|---|
| 1 | Replace debug `print` in client with structlog | `llm/client.py` |
| 2 | Integration test: seed DB + mock LLM + verify tool loop hits SQL | `tests/test_agents.py` |
| 3 | Run eval harness end-to-end, add more labeled payments | `eval/harness.py` |
| 4 | Log token usage from OpenRouter responses | `llm/client.py`, `observability/logging.py` |
| 5 | Update README to reflect tool-use architecture | `README.md` |
