# Multi-agent beneficiary risk

## Objective
Prototype a multi-agent system that evaluates whether a payment recipient
is safe. Your solution should demonstrate how you build reliable infrastructure
for non-deterministic components: agent orchestration, failure handling,
information boundaries, and observability — not the quality of the risk
assessment itself.

### Scenario
Tunic Pay runs real-time investigations on payments before they clear. When a
bank sends us a payment for review, an orchestrator plans an investigation,
delegates work to specialised agents, and synthesises their findings into a
structured risk decision.
Your task is to build this orchestration layer.

### Input
The system receives a payment object:
```
{
    "payment_id": "pay_abc123",
    "sender": {
        "name": "Jane Smith",
        "account_id": "GB82WEST12345698765432",
        "bank": "NatWest"
    },
    "recipient": {
        "name": "Acme Consulting Ltd",
        "account_id": "GB29NWBK60161331926819",
        "bank": "Barclays"
    },
    "amount": 4500.00,
    "currency": "GBP",
    "reference": "Invoice 2024-0892",
    "timestamp": "2025-06-15T14:32:00Z"
}
```

### Requirements
1. Knowledge layer
Provide a static knowledge base (files, SQLite, or similar) that simulates the
heterogeneous data sources agents would query in production. For example:
- Company registry data (e.g. incorporation date, status, directors, filing
history)
- Adverse media (e.g. news articles, scam reports)
- Payment history (e.g. prior transactions involving this recipient)
- Sanctions/PEP lists (e.g. a simple lookup table)
Include 3–5 recipients with varying risk profiles (clearly safe, clearly risky,
ambiguous). This keeps the exercise focused on system design rather than
data sourcing.
Information boundaries: Each agent should only have access to the data it
needs — not the entire knowledge base. How you enforce this is up to you
(separate retrieval functions, scoped tool access, filtered context injection,
etc.), but an agent checking company history should not see sanctions data,
and vice versa.

2. Orchestration
- An orchestrator (agent or deterministic) that receives a payment, plans
which agents to invoke, dispatches work, and synthesises results into a
final risk decision.
- Feel free to make liberal use of off-the-shelf technologies — workflow
orchestrators (e.g. Temporal, Prefect), vector stores, task queues, etc.
We're interested in your judgement about when to reach for existing tools
vs. roll your own.
- Agents that don't depend on each other should run concurrently.
- The orchestrator should produce a structured JSON result including the
individual agent assessments and the aggregated decision.

3. Agents
- 3+ specialised agents, each responsible for a distinct risk dimension (e.g.
company verification, adverse media analysis, payment pattern analysis,
sanctions screening). Agents can be simple — even a single LLM call with a
focused prompt is fine.
- Each agent must return a structured result conforming to a defined
schema (e.g. risk signal, confidence, evidence summary, reasoning).
- Use real LLM calls via OpenRouter (API key will be provided; you can also
use it for code assistance during development). Any model available on
OpenRouter is fine.

4. Reliability and observability
This is where we'll focus evaluation:
- Failure tolerance: What happens when an agent times out, returns
malformed output, or errors? The system should degrade gracefully —
partial results are better than no results.
- Output contracts: Validate that each agent's output conforms to its
expected schema before it feeds into downstream processing. Handle
violations explicitly.
- Observability: An operator (or auditor) should be able to trace a payment
investigation: which agents ran, what context they received, what they
returned, how long they took, and how the final decision was reached.
Structured logging is sufficient — no need for a tracing UI.
- Reproducibility: How do you manage non-determinism from LLM calls?
Document your approach (e.g. temperature settings, seed parameters, retry
strategies).

5. Additional goals
- Evaluation harness: Given a set of test payments with known-good risk
labels, measure system accuracy and/or consistency across repeated runs.
Even a simple script that runs N payments and reports results is valuable.
- Agent guardrails: Demonstrate at least one mechanism that constrains
agent behaviour beyond output validation (e.g. token budgets, tool-use
restrictions, retry with corrective prompting).

### Implementation
- Write basic, readable code in a stack of your choosing (clarity over
complexity). Python is fine; so is anything else.
- Use LLMs thoughtfully. This is an infrastructure exercise — the agents can
be thin wrappers around LLM calls, but the orchestration, error handling,
information boundaries, and contracts around them should be solid.
- Apply sound engineering practices: clear separation of concerns,
structured logging, basic tests for the orchestration layer (not the LLM
outputs).
- We strongly encourage the use of development tools such as Cursor.
- Make (and document) reasonable product assumptions where
requirements are ambiguous.

### Deliverrables
- Implementation
- The static knowledge base with sample recipients
- A README explaining: how to run the system, architecture and key
design decisions, trade-offs you made, and what you'd do differently
with more time
- Example inputs and outputs (can be included in the README or as fixture
files)

### Evaluation criteria
We will assess:
1. System design: Orchestration patterns, agent contracts, information
boundaries. Could we add a 4th agent without touching existing ones?
2. Infrastructure choices: Tool selection and justification, concurrency model,
knowledge layer design.
3. Failure handling: What happens when things go wrong? Timeouts,
malformed outputs, partial failures.
4. Observability: Can we trace a payment through the system and understand
why it got its risk score?
5. Core SWE: Code structure, testing approach, error handling,
typing/contracts.
6. LLM integration: Schema enforcement, prompt structure, handling of non-
determinism.
7. Product instincts: Does the system make sensible assumptions? Is the
output useful?

### Questions for considerations
- How would you handle a case where one agent strongly disagrees with the
others?
- What should the system do if the most critical agent (say, sanctions
screening) fails but the others succeed?
- How would you version agent prompts and track whether a prompt change
improved or degraded results?
- If this system needed to handle 1,000 payments/minute, what would you
change?
- What's the right boundary between what the orchestrator decides
deterministically vs. what it delegates to an LLM?