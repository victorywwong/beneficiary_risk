# Progress Against PRD Requirements

## Requirement 1 — Knowledge Layer

- ✅ Static knowledge base: SQLite (`knowledge/risk.db`) with 4 tables
- ✅ Company registry data: incorporation date, status, directors, filing status, country
- ✅ Adverse media: headline, source, published date, severity
- ✅ Payment history: total transactions, avg amount, large tx count, flagged count
- ✅ Sanctions / PEP list: list type, reason, listed date
- ✅ 5 recipients with varied risk profiles:
  - **TechFlow Solutions** — clearly safe (clean history, active, no hits)
  - **Green Energy Partners** — clearly safe (new, clean)
  - **Acme Consulting Ltd** — ambiguous (active, one old low-severity media hit)
  - **Nova Import Export** — risky (PEP connection, unusual payment patterns)
  - **FastCash Holdings** — clearly high risk (sanctions hit + adverse media + flagged payments)
- ✅ Information boundaries enforced: each agent has a single scoped `db_tools` entry and `_execute_db_tool` only dispatches to its own `database.py` function — company agent cannot call `get_sanctions_data`, etc.

---

## Requirement 2 — Orchestration

- ✅ Orchestrator plans investigation: `activities/planner.py` — LLM decides which agents to invoke per payment
- ✅ Uses off-the-shelf orchestrator: Temporal (durable execution, retry, timeout, Web UI audit trail)
- ✅ Parallel execution: `asyncio.gather` over agent activities in `workflows/investigate.py`
- ✅ Structured JSON result: `RiskDecision` includes individual `agent_results` list + `decision`, `aggregate_risk`, `confidence`, `reasoning`, `trace_id`
- ✅ Sanctions hard guardrail: always appended to plan post-LLM regardless of planner output

---

## Requirement 3 — Agents

- ✅ 4 specialised agents: `CompanyAgent`, `AdverseMediaAgent`, `PaymentPatternAgent`, `SanctionsAgent`
- ✅ Each agent responsible for a distinct risk dimension
- ✅ Structured result schema: `AgentResult` — `risk_signal`, `confidence`, `evidence_summary`, `reasoning`, `is_available`, `error`, `duration_ms`
- ✅ Schema enforced at output: Pydantic v2 `model_validate` on every agent response
- ✅ Real LLM calls via OpenRouter (`AsyncOpenAI` client pointing to `openrouter.ai/api/v1`)
- ✅ `response_format=json_schema` used for structured assessment output

---

## Requirement 4 — Reliability and Observability

### Failure tolerance
- ✅ Agent timeout → returns `AgentResult(is_available=False, error="timeout")` — never crashes workflow
- ✅ Agent exception → returns `AgentResult(is_available=False, error=...)` — graceful degradation
- ✅ Sanctions unavailable → synthesizer forces `REVIEW` (cannot approve without sanctions clearance)
- ✅ Planner failure → falls back to all-agents plan (logged as `planner_fallback`)
- ✅ Temporal retries: each activity has `RetryPolicy(maximum_attempts=2)`
- ✅ `MAX_TOOL_ITERATIONS = 5` guard on agent tool loop

### Output contracts
- ✅ Every agent output validated via `AgentResult.model_validate()` before reaching synthesizer
- ✅ Planner output validated via `OrchestratorPlan.model_validate()`
- ✅ Final decision validated via `RiskDecision` Pydantic model

### Observability
- ✅ structlog configured with JSON renderer and trace context binding (`observability/logging.py`)
- ✅ `trace_id` bound to each investigation (via `workflow.uuid4()`)
- ✅ `agent_completed` event: agent name, risk_signal, confidence, duration_ms
- ✅ `agent_failed` event: agent name, error, duration_ms
- ✅ `llm_call` event: agent name, prompt version
- ✅ `tool_result` event: agent name, tool name
- ✅ `decision_reached` event: decision, payment_id
- ✅ `duration_ms` on every `AgentResult`
- ✅ Full workflow history in Temporal Web UI (`localhost:8080`)
- 🔧 `llm/client.py` still uses `print()` for debug output — should use structlog
- ⬜ Token usage not logged (available from OpenRouter response but not captured)
- ⬜ Tool call arguments not explicitly logged (what context agents received)

### Reproducibility
- ✅ `temperature=0.0` on all LLM calls (enforced in `client.complete`)
- ✅ Prompt versions tracked (`COMPANY_PROMPT_VERSION = "company_v3"` etc.) and logged with each call
- ✅ Deterministic synthesizer — same agent results always produce the same decision
- ⬜ Prompt version not included in `AgentResult` output (would help trace which prompt version produced which result)

---

## Requirement 5 — Additional Goals

### Evaluation harness
- ✅ `eval/harness.py` exists: runs labeled payments N times, reports accuracy + consistency per payment
- ⬜ Not yet run end-to-end against live Temporal + LLM
- ⬜ Only 2 labeled payments defined (safe: TechFlow, high-risk: FastCash)

### Agent guardrails
- ✅ Token budgets: `max_tokens=512` enforced on every LLM call
- ✅ Tool-use restrictions: each agent's `db_tools` is scoped — `CompanyAgent` cannot call `get_sanctions_data`
- ✅ Sanctions always required: hard-coded guardrail in both `workflows/investigate.py` and `orchestrator/synthesizer.py`
- ✅ `MAX_TOOL_ITERATIONS` cap: prevents runaway tool-calling loops
- ⬜ Retry with corrective prompting: removed when switching to tool use + `response_format` (schema enforcement now happens at API level — acceptable trade-off)

---

## Deliverables

- ✅ Implementation — complete and smoke-tested
- ✅ Static knowledge base with sample recipients — `knowledge/seed.py` + `risk.db`
- 🔧 README — exists but describes old pre-fetch architecture; needs update for tool-use design
- ✅ Example inputs — `tests/fixtures/payments.json`
- ⬜ Example outputs — no sample output JSON in README or fixtures yet

---

## Remaining Work (Priority Order)

| # | Item | File(s) | PRD section |
|---|---|---|---|
| 1 | Replace `print()` with structlog in client | `llm/client.py` | Req 4 — Observability |
| 2 | Log token usage from OpenRouter response | `llm/client.py` | Req 4 — Observability |
| 3 | Log tool call arguments (what context agents received) | `agents/base.py` | Req 4 — Observability |
| 4 | Run eval harness e2e, expand labeled payments to 5 | `eval/harness.py` | Req 5 — Eval harness |
| 5 | Add prompt_version to AgentResult output | `schemas/agent_result.py`, agents | Req 4 — Reproducibility |
| 6 | Update README for tool-use architecture + add example output | `README.md` | Deliverables |
