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
- `schemas/agent_result.py` — `AgentResult`, `RiskSignal` (includes `prompt_version`, `duration_ms`)
- `schemas/orchestrator_plan.py` — `OrchestratorPlan`, `AgentType`
- `schemas/risk_decision.py` — `RiskDecision`, `Decision`

## Step 3 — Knowledge Base ✅
- `knowledge/schema.sql` — 4 tables: company_registry, adverse_media, payment_history, sanctions_pep
- `knowledge/seed.py` — 5 recipients with varied risk profiles
- `knowledge/database.py` — scoped query functions (information boundary enforcement)

## Step 4 — LLM Client ✅
- `llm/client.py` — `AsyncOpenAI` → OpenRouter, supports `tools` + `response_format`
- Logs `llm_response` event: model, prompt_tokens, completion_tokens, total_tokens via structlog
- Conditional Langfuse import: uses `langfuse.openai.AsyncOpenAI` when `LANGFUSE_PUBLIC_KEY` is set

## Step 5 — Base Agent ✅
- `agents/base.py` — agentic tool-use loop (DB lookups via tool calls) + `response_format` for structured output
- Timeout and exception → unavailable `AgentResult` (graceful degradation)
- `MAX_TOOL_ITERATIONS = 5` guard
- `@observe(name="tool_loop")` and `@observe(name="db_tool")` Langfuse spans (no-op when not configured)

## Step 6 — Specialist Agents ✅
- `agents/company_agent.py` — `GET_COMPANY_DATA_TOOL`, `prompt_version = COMPANY_PROMPT_VERSION`
- `agents/adverse_media_agent.py` — `GET_ADVERSE_MEDIA_TOOL`, `prompt_version = ADVERSE_MEDIA_PROMPT_VERSION`
- `agents/payment_pattern_agent.py` — `GET_PAYMENT_HISTORY_TOOL`, `prompt_version = PAYMENT_PATTERN_PROMPT_VERSION`
- `agents/sanctions_agent.py` — `GET_SANCTIONS_DATA_TOOL`, `prompt_version = SANCTIONS_PROMPT_VERSION`
- Each: scoped DB tool, `_execute_db_tool` dispatch, `prompt_version` propagated to `AgentResult`

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
- Thresholds: REVIEW ≥ 0.1, REJECT ≥ 0.6 (score = sum of weight × signal, no confidence factor)

## Step 9 — Observability ✅
- `observability/logging.py` — structlog JSON with trace context
- `llm/client.py` — `llm_response` event with token usage per call
- `agents/base.py` — `tool_result` event with tool name and args
- Langfuse: conditional `langfuse.openai.AsyncOpenAI` wrapper + `@observe` spans on tool loop and DB dispatch

## Step 10 — Entry Points ✅
- `main.py` — `--payment-file` CLI, submits workflow, prints JSON result
- `worker.py` — Temporal worker

## Step 11 — Tests ✅
- `tests/test_synthesizer.py` — 6 unit tests (all hard rules + weighted scoring)
- `tests/test_agents.py` — 3 unit tests (tool loop, timeout, exception)
- `tests/test_workflow.py` — 4 integration tests via `TestWorkflowEnvironment`
- All 13 tests passing

## Step 12 — Evaluation Harness ✅
- `eval/harness.py` — runs labeled payments N times, reports accuracy + consistency per payment
- All 5 recipients covered as labeled cases:
  - TechFlow Solutions → APPROVE (safe, established)
  - Green Energy Partners → APPROVE (safe, established, clean history)
  - Acme Consulting Ltd → REVIEW (old adverse media hit)
  - Nova Import Export → REVIEW (PEP connection + payment flags)
  - FastCash Holdings → REJECT (OFAC sanctions)
- Current eval results: **100% accuracy, 100% consistency** (5/5 correct across 3 runs each)
- Prompt tuning iterated across multiple versions to reach these results:
  - `sanctions_v4`: distinguishes PEP (MEDIUM) from actual sanctions (HIGH)
  - `adverse_media_v5`: bases HIGH/MEDIUM strictly on `severity` field value in DB
  - `company_v4`: strict 12-month rule for "recently incorporated"
  - `payment_pattern_v4`: zero flagged = LOW regardless of payment size

## Step 13 — README ✅
- Updated to reflect tool-use architecture, Langfuse integration, example output, trade-offs, PRD answers

---

## Remaining Work

None — all steps complete.
