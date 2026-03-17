"""Deterministic risk synthesizer — no LLM involved."""
from datetime import datetime, timezone
from schemas.agent_result import AgentResult, RiskSignal
from schemas.orchestrator_plan import OrchestratorPlan
from schemas.payment import Payment
from schemas.risk_decision import Decision, RiskDecision

AGENT_WEIGHTS = {
    "sanctions": 0.4,
    "company": 0.25,
    "adverse_media": 0.25,
    "payment_pattern": 0.1,
}

SIGNAL_SCORES = {
    RiskSignal.HIGH: 1.0,
    RiskSignal.MEDIUM: 0.5,
    RiskSignal.LOW: 0.0,
    RiskSignal.UNKNOWN: 0.5,  # treat unknown as medium risk
}

REVIEW_THRESHOLD = 0.1
REJECT_THRESHOLD = 0.6


def synthesize(
    payment: Payment,
    plan: OrchestratorPlan,
    agent_results: list[AgentResult],
    trace_id: str,
) -> RiskDecision:
    results_by_name = {r.agent_name: r for r in agent_results}
    sanctions = results_by_name.get("sanctions")

    reasoning_parts = []

    # Hard rule 1: sanctions agent unavailable → force REVIEW
    if sanctions is None or not sanctions.is_available:
        reasoning_parts.append("REVIEW forced: sanctions agent unavailable — cannot approve without sanctions clearance.")
        return RiskDecision(
            payment_id=payment.payment_id,
            decision=Decision.REVIEW,
            aggregate_risk=RiskSignal.UNKNOWN,
            confidence=0.0,
            agent_results=agent_results,
            reasoning=" | ".join(reasoning_parts),
            trace_id=trace_id,
            investigated_at=datetime.now(timezone.utc),
        )

    # Hard rule 2: sanctions HIGH → REJECT immediately
    if sanctions.risk_signal == RiskSignal.HIGH:
        reasoning_parts.append(f"REJECT: sanctions agent returned HIGH risk (confidence={sanctions.confidence:.2f}). {sanctions.evidence_summary}")
        return RiskDecision(
            payment_id=payment.payment_id,
            decision=Decision.REJECT,
            aggregate_risk=RiskSignal.HIGH,
            confidence=sanctions.confidence,
            agent_results=agent_results,
            reasoning=" | ".join(reasoning_parts),
            trace_id=trace_id,
            investigated_at=datetime.now(timezone.utc),
        )

    # Weighted scoring of available agents
    total_weight = 0.0
    weighted_score = 0.0
    available_count = 0

    for result in agent_results:
        if not result.is_available:
            reasoning_parts.append(f"{result.agent_name}: UNAVAILABLE ({result.error})")
            continue
        weight = AGENT_WEIGHTS.get(result.agent_name, 0.1)
        score = SIGNAL_SCORES[result.risk_signal]
        weighted_score += weight * score
        total_weight += weight
        available_count += 1
        reasoning_parts.append(
            f"{result.agent_name}: {result.risk_signal} (confidence={result.confidence:.2f}) — {result.evidence_summary}"
        )

    if total_weight == 0:
        final_score = 0.5
        aggregate_confidence = 0.0
    else:
        final_score = weighted_score / total_weight
        aggregate_confidence = available_count / len(agent_results)

    # Map score to aggregate risk signal
    if final_score >= REJECT_THRESHOLD:
        aggregate_risk = RiskSignal.HIGH
    elif final_score >= REVIEW_THRESHOLD:
        aggregate_risk = RiskSignal.MEDIUM
    else:
        aggregate_risk = RiskSignal.LOW

    # Map to decision
    if aggregate_risk == RiskSignal.HIGH:
        decision = Decision.REJECT
    elif aggregate_risk == RiskSignal.MEDIUM:
        decision = Decision.REVIEW
    else:
        decision = Decision.APPROVE

    reasoning_parts.append(f"Weighted score={final_score:.3f} → {decision}")

    return RiskDecision(
        payment_id=payment.payment_id,
        decision=decision,
        aggregate_risk=aggregate_risk,
        confidence=aggregate_confidence,
        agent_results=agent_results,
        reasoning=" | ".join(reasoning_parts),
        trace_id=trace_id,
        investigated_at=datetime.now(timezone.utc),
    )
