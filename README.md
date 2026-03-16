# Beneficiary Risk Assessment System

A multi-agent payment risk assessment prototype for Tunic Pay. Receives a payment object, runs parallel specialist agents against a static knowledge base, and synthesises findings into a structured risk decision.

## Architecture

```
Payment → [Temporal Workflow]
            │
            ├── 1. LLM Planner
            │       └── tool call: plan_investigation → OrchestratorPlan
            │
            ├── 2. Parallel agent activities (fan-out)
            │       │
            │       ├── CompanyAgent
            │       │     ├── LLM calls get_company_data(account_id)
            │       │     ├── SQLite query → result appended to context
            │       │     └── LLM returns structured assessment (response_format)
            │       │
            │       ├── AdverseMediaAgent       (same agentic loop pattern)
            │       ├── PaymentPatternAgent     (same agentic loop pattern)
            │       └── SanctionsAgent          (same agentic loop pattern)
            │
            └── 3. Deterministic Synthesizer → RiskDecision
```

Each agent runs an **agentic tool-use loop**: the LLM calls its scoped DB tool to fetch data, receives the result, then produces a structured risk assessment via `response_format=json_schema`. The agent never receives data it didn't explicitly request.

## Tech Stack

| Concern | Choice |
|---|---|
| Orchestration | Temporal (durable execution, retry/timeout, Web UI audit trail) |
| LLM API | `openai` SDK → OpenRouter (`AsyncOpenAI(base_url="openrouter.ai/api/v1")`) |
| Structured output | `response_format=json_schema` for agent assessments; tool use for DB lookups |
| Schema validation | Pydantic v2 |
| Knowledge base | SQLite (`knowledge/risk.db`) |
| Logging | structlog (JSON, trace context) |

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY and MODEL_ID

# 3. Seed knowledge base
python3 knowledge/seed.py

# 4. Start Temporal server (pick one)

# Option A — Temporal CLI (recommended, no Docker required)
brew install temporal
temporal server start-dev   # gRPC :7233, Web UI :8233

# Option B — Docker Compose (Temporal + PostgreSQL + Web UI on :8080)
docker compose up -d

# 5. Start worker (keep running in a separate terminal)
python3 worker.py

# 6. Submit payments
python3 main.py --payment-file tests/fixtures/payments.json
```

## Running Tests

```bash
pytest tests/
```

Uses Temporal's `TestWorkflowEnvironment` — no running server needed. All 13 tests pass with mocked LLM calls.

## Key Design Decisions

### Agents fetch their own data via tool calls (information boundary)
Each agent is given only the tool schema for its own data source. `CompanyAgent` has `get_company_data`; `SanctionsAgent` has `get_sanctions_data`. The LLM must call its tool to retrieve data — it cannot access another agent's data source. This enforces information boundaries at the API level rather than through context injection.

### Deterministic synthesizer — no LLM in the decision path
The LLM is used for two things: planning (which agents to run) and evidence gathering (each agent's structured assessment). The final aggregation is fully deterministic — weighted scoring with hard rules — and is unit-testable independently of any LLM.

### Sanctions always required (hard guardrail)
Two enforcement points: (1) the workflow appends `sanctions` to the plan post-LLM regardless of what the planner returns, and (2) the synthesizer forces `REVIEW` if the sanctions agent is unavailable. The system cannot `APPROVE` without a sanctions clearance.

### Temporal for orchestration
Durable execution means a worker restart resumes mid-workflow. Retry policies, timeouts, and the full activity history are configured declaratively. The Temporal Web UI provides a complete audit trail per payment. Workflow ID = `payment_id` gives natural deduplication.

### Temperature = 0 for reproducibility
All LLM calls use `temperature=0.0`. Prompt versions are tracked as constants (e.g. `COMPANY_PROMPT_VERSION = "company_v3"`) and logged with every call, making it straightforward to correlate a result to the exact prompt that produced it.

## Knowledge Base

Five recipients seeded in `knowledge/seed.py`:

| Recipient | Account | Risk Profile |
|---|---|---|
| TechFlow Solutions | GB82WEST12345698765433 | Safe — established, clean history |
| Green Energy Partners | GB82WEST12345698765500 | Safe — new company, no flags |
| Acme Consulting Ltd | GB29NWBK60161331926819 | Ambiguous — active, one old media hit |
| Nova Import Export | GB29NWBK60161388888888 | Risky — PEP connection, unusual patterns |
| FastCash Holdings | GB29NWBK60161399999999 | High risk — sanctions hit + adverse media |

## Example Input / Output

**Input** (`tests/fixtures/payments.json`):
```json
{
  "payment_id": "pay_003",
  "sender": { "name": "Alice Corp", "account_id": "GB29NWBK60161300000001", "bank": "Barclays" },
  "recipient": { "name": "TechFlow Solutions", "account_id": "GB82WEST12345698765433", "bank": "Westpac" },
  "amount": 8500.0,
  "currency": "GBP",
  "reference": "Software licence renewal",
  "timestamp": "2024-11-15T12:00:00Z"
}
```

**Output**:
```json
{
  "payment_id": "pay_003",
  "decision": "APPROVE",
  "aggregate_risk": "LOW",
  "confidence": 1.0,
  "agent_results": [
    {
      "agent_name": "company",
      "risk_signal": "LOW",
      "confidence": 0.95,
      "evidence_summary": "TechFlow Solutions is an active company incorporated in 2005 with up-to-date filings.",
      "reasoning": "Long-established active company, clean filing history, no dormancy indicators.",
      "is_available": true,
      "duration_ms": 1842.3
    },
    {
      "agent_name": "adverse_media",
      "risk_signal": "LOW",
      "confidence": 0.95,
      "evidence_summary": "No adverse media records found for this account.",
      "reasoning": "No news articles, scam reports, or negative coverage found.",
      "is_available": true,
      "duration_ms": 1654.1
    },
    {
      "agent_name": "payment_pattern",
      "risk_signal": "LOW",
      "confidence": 0.9,
      "evidence_summary": "312 prior transactions, avg GBP 8,750, zero flagged. Current payment within normal range.",
      "reasoning": "High transaction volume with no flags. Current amount consistent with historical average.",
      "is_available": true,
      "duration_ms": 1721.8
    },
    {
      "agent_name": "sanctions",
      "risk_signal": "LOW",
      "confidence": 0.99,
      "evidence_summary": "No sanctions or PEP matches found.",
      "reasoning": "No entries in sanctions or PEP lists for this account or name.",
      "is_available": true,
      "duration_ms": 1389.5
    }
  ],
  "reasoning": "company: LOW (confidence=0.95) | adverse_media: LOW (confidence=0.95) | payment_pattern: LOW (confidence=0.90) | sanctions: LOW (confidence=0.99) | Weighted score=0.000 → APPROVE",
  "trace_id": "a3f1c2d4-7e8b-4a9c-b1d2-e3f4a5b6c7d8",
  "investigated_at": "2024-11-15T12:00:05.123Z"
}
```

## Trade-offs and What I'd Do Differently

**SQLite → Postgres/document store in production**: SQLite is easy to seed and inspect but single-writer. Production would use Postgres (already in `docker-compose.yml`) or a document store per data domain.

**`response_format` support varies by model**: Not all OpenRouter models support `json_schema`. A fallback to `{"type": "json_object"}` with schema validation in the agent would improve portability.

**Single retry on tool loop**: `MAX_TOOL_ITERATIONS = 5` is conservative. In practice, simple single-table agents need at most 2 iterations (one tool call + one assessment). A per-agent iteration budget would be more precise.

**Prompt versioning is manual**: Version constants (`company_v3`) are logged but not tied to evaluation metrics. With more time: store prompt versions in a registry, run the eval harness on each change, and gate deploys on consistency thresholds.

**Eval harness not yet run live**: `eval/harness.py` exists with labeled payments but hasn't been validated against a live Temporal + LLM run. With more time: add all 5 recipients as labeled cases and automate in CI.

## Answers to PRD Questions

**How would you handle a case where one agent strongly disagrees with the others?**
Currently: weighted scoring means a single dissenting agent can only shift the result if its weight is large enough. For sanctions (weight 0.4) a HIGH is a hard REJECT regardless. For others, a high-confidence HIGH from one agent against LOW from the rest would produce a REVIEW. With more time I'd log the disagreement explicitly and potentially flag it for human review.

**What should the system do if the most critical agent (sanctions) fails but the others succeed?**
Implemented: `synthesizer.py` forces `REVIEW` if the sanctions agent is unavailable. The system cannot approve without a sanctions clearance — this is the `is_available=False` → REVIEW hard rule.

**How would you version agent prompts and track whether a prompt change improved or degraded results?**
Prompt version constants are logged with every LLM call. The eval harness is designed to run labeled payments N times. The missing link is storing (prompt_version, payment_id, decision) tuples and diffing across versions — straightforward to add to `eval/harness.py`.

**If this system needed to handle 1,000 payments/minute, what would you change?**
Temporal handles horizontal scaling by adding workers. The bottlenecks would be: (1) OpenRouter rate limits — mitigate with multiple API keys or a self-hosted model, (2) SQLite → Postgres (already in docker-compose), (3) worker pool sizing. The workflow/activity structure is already designed for this — no code changes to the orchestration logic needed.

**What's the right boundary between deterministic vs. LLM decisions?**
Implemented boundary: LLM decides *which* agents to run (planning) and *what the evidence means* (assessment). Everything else is deterministic: the sanctions guardrail, the weighted aggregation, the APPROVE/REVIEW/REJECT thresholds. The synthesizer is fully unit-testable without any LLM. This boundary means the system's decision logic can be audited, reasoned about, and changed without touching prompts.
