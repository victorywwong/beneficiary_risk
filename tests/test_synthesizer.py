"""Unit tests for the deterministic synthesizer."""
import pytest
from datetime import datetime, timezone
from schemas.agent_result import AgentResult, RiskSignal
from schemas.orchestrator_plan import AgentType, OrchestratorPlan
from schemas.payment import Payment, Sender, Recipient
from schemas.risk_decision import Decision
from orchestrator.synthesizer import synthesize


@pytest.fixture
def payment():
    return Payment(
        payment_id="pay_test",
        sender=Sender(name="Test Sender", account_id="SENDER001", bank="Test Bank"),
        recipient=Recipient(name="Test Recipient", account_id="RECV001", bank="Test Bank"),
        amount=10000.0,
        currency="GBP",
        reference="Test payment",
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def plan():
    return OrchestratorPlan(
        agents_to_run=[AgentType.COMPANY, AgentType.ADVERSE_MEDIA, AgentType.PAYMENT_PATTERN, AgentType.SANCTIONS],
        reasoning="All agents selected",
    )


def make_result(name: str, signal: RiskSignal, confidence: float = 0.9) -> AgentResult:
    return AgentResult(
        agent_name=name,
        risk_signal=signal,
        confidence=confidence,
        evidence_summary=f"{name} evidence",
        reasoning=f"{name} reasoning",
        is_available=True,
        duration_ms=100.0,
    )


def make_failed(name: str) -> AgentResult:
    return AgentResult(
        agent_name=name,
        risk_signal=RiskSignal.UNKNOWN,
        confidence=0.0,
        evidence_summary="Agent failed",
        reasoning="timeout",
        is_available=False,
        error="timeout",
        duration_ms=30000.0,
    )


class TestSanctionsHardRules:
    def test_sanctions_high_forces_reject(self, payment, plan):
        results = [
            make_result("company", RiskSignal.LOW),
            make_result("adverse_media", RiskSignal.LOW),
            make_result("payment_pattern", RiskSignal.LOW),
            make_result("sanctions", RiskSignal.HIGH),
        ]
        decision = synthesize(payment, plan, results, "trace_001")
        assert decision.decision == Decision.REJECT
        assert decision.aggregate_risk == RiskSignal.HIGH

    def test_sanctions_unavailable_forces_review(self, payment, plan):
        results = [
            make_result("company", RiskSignal.LOW),
            make_result("adverse_media", RiskSignal.LOW),
            make_result("payment_pattern", RiskSignal.LOW),
            make_failed("sanctions"),
        ]
        decision = synthesize(payment, plan, results, "trace_002")
        assert decision.decision == Decision.REVIEW

    def test_sanctions_missing_forces_review(self, payment, plan):
        results = [
            make_result("company", RiskSignal.LOW),
            make_result("adverse_media", RiskSignal.LOW),
        ]
        decision = synthesize(payment, plan, results, "trace_003")
        assert decision.decision == Decision.REVIEW


class TestWeightedScoring:
    def test_all_low_approves(self, payment, plan):
        results = [
            make_result("company", RiskSignal.LOW),
            make_result("adverse_media", RiskSignal.LOW),
            make_result("payment_pattern", RiskSignal.LOW),
            make_result("sanctions", RiskSignal.LOW),
        ]
        decision = synthesize(payment, plan, results, "trace_004")
        assert decision.decision == Decision.APPROVE

    def test_multiple_high_rejects(self, payment, plan):
        results = [
            make_result("company", RiskSignal.HIGH),
            make_result("adverse_media", RiskSignal.HIGH),
            make_result("payment_pattern", RiskSignal.MEDIUM),
            make_result("sanctions", RiskSignal.LOW),
        ]
        decision = synthesize(payment, plan, results, "trace_005")
        assert decision.decision in (Decision.REVIEW, Decision.REJECT)

    def test_mixed_signals_review(self, payment, plan):
        results = [
            make_result("company", RiskSignal.MEDIUM),
            make_result("adverse_media", RiskSignal.MEDIUM),
            make_result("payment_pattern", RiskSignal.LOW),
            make_result("sanctions", RiskSignal.LOW),
        ]
        decision = synthesize(payment, plan, results, "trace_006")
        assert decision.decision in (Decision.REVIEW, Decision.APPROVE)
