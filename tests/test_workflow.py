"""Temporal workflow tests using TestWorkflowEnvironment."""
import pytest
from datetime import datetime, timezone
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from temporalio.contrib.pydantic import pydantic_data_converter

from workflows.investigate import InvestigatePaymentWorkflow
from schemas.payment import Payment, Sender, Recipient
from schemas.agent_result import AgentResult, RiskSignal
from schemas.orchestrator_plan import AgentType, OrchestratorPlan
from schemas.risk_decision import Decision


@pytest.fixture
def payment():
    return Payment(
        payment_id="pay_workflow_test",
        sender=Sender(name="Test Sender", account_id="SENDER001", bank="Test Bank"),
        recipient=Recipient(name="Test Recipient", account_id="RECV001", bank="Test Bank"),
        amount=10000.0,
        currency="GBP",
        reference="Test payment",
        timestamp=datetime.now(timezone.utc),
    )


def make_result(name: str, signal: RiskSignal) -> AgentResult:
    return AgentResult(
        agent_name=name,
        risk_signal=signal,
        confidence=0.9,
        evidence_summary=f"{name} check passed",
        reasoning=f"{name} analysis complete",
        is_available=True,
        duration_ms=100.0,
    )


def make_failed_result(name: str) -> AgentResult:
    return AgentResult(
        agent_name=name,
        risk_signal=RiskSignal.UNKNOWN,
        confidence=0.0,
        evidence_summary="Agent unavailable",
        reasoning="timeout",
        is_available=False,
        error="timeout",
        duration_ms=30000.0,
    )


# --- Shared mock activities ---

@activity.defn(name="plan_investigation")
async def mock_plan_all_clear(p: Payment) -> OrchestratorPlan:
    return OrchestratorPlan(
        agents_to_run=[AgentType.COMPANY, AgentType.ADVERSE_MEDIA, AgentType.PAYMENT_PATTERN, AgentType.SANCTIONS],
        reasoning="All agents",
    )

@activity.defn(name="run_company_agent")
async def mock_company_low(p: Payment) -> AgentResult:
    return make_result("company", RiskSignal.LOW)

@activity.defn(name="run_adverse_media_agent")
async def mock_adverse_media_low(p: Payment) -> AgentResult:
    return make_result("adverse_media", RiskSignal.LOW)

@activity.defn(name="run_payment_pattern_agent")
async def mock_payment_pattern_low(p: Payment) -> AgentResult:
    return make_result("payment_pattern", RiskSignal.LOW)

@activity.defn(name="run_sanctions_agent")
async def mock_sanctions_low(p: Payment) -> AgentResult:
    return make_result("sanctions", RiskSignal.LOW)


# --- Test 1: all clear → APPROVE ---

async def test_workflow_all_clear_approves(payment):
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[InvestigatePaymentWorkflow],
            activities=[mock_plan_all_clear, mock_company_low, mock_adverse_media_low, mock_payment_pattern_low, mock_sanctions_low],
        ):
            result = await env.client.execute_workflow(
                InvestigatePaymentWorkflow.run,
                payment,
                id="test-wf-001",
                task_queue="test-queue",
            )
    assert result.decision == Decision.APPROVE
    assert result.payment_id == payment.payment_id


# --- Test 2: sanctions HIGH → REJECT ---

@activity.defn(name="run_sanctions_agent")
async def mock_sanctions_high(p: Payment) -> AgentResult:
    return make_result("sanctions", RiskSignal.HIGH)


async def test_workflow_sanctions_high_rejects(payment):
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[InvestigatePaymentWorkflow],
            activities=[mock_plan_all_clear, mock_company_low, mock_adverse_media_low, mock_payment_pattern_low, mock_sanctions_high],
        ):
            result = await env.client.execute_workflow(
                InvestigatePaymentWorkflow.run,
                payment,
                id="test-wf-002",
                task_queue="test-queue",
            )
    assert result.decision == Decision.REJECT


# --- Test 3: sanctions unavailable → REVIEW ---

@activity.defn(name="run_sanctions_agent")
async def mock_sanctions_unavailable(p: Payment) -> AgentResult:
    return make_failed_result("sanctions")


async def test_workflow_sanctions_unavailable_forces_review(payment):
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[InvestigatePaymentWorkflow],
            activities=[mock_plan_all_clear, mock_company_low, mock_adverse_media_low, mock_payment_pattern_low, mock_sanctions_unavailable],
        ):
            result = await env.client.execute_workflow(
                InvestigatePaymentWorkflow.run,
                payment,
                id="test-wf-003",
                task_queue="test-queue",
            )
    assert result.decision == Decision.REVIEW


# --- Test 4: planner fallback → all agents → APPROVE ---

@activity.defn(name="plan_investigation")
async def mock_plan_fallback(p: Payment) -> OrchestratorPlan:
    return OrchestratorPlan(
        agents_to_run=[AgentType.COMPANY, AgentType.ADVERSE_MEDIA, AgentType.PAYMENT_PATTERN, AgentType.SANCTIONS],
        reasoning="Planner failed, falling back to all agents",
    )


async def test_workflow_planner_fallback_runs_all_agents(payment):
    async with await WorkflowEnvironment.start_time_skipping(
        data_converter=pydantic_data_converter
    ) as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[InvestigatePaymentWorkflow],
            activities=[mock_plan_fallback, mock_company_low, mock_adverse_media_low, mock_payment_pattern_low, mock_sanctions_low],
        ):
            result = await env.client.execute_workflow(
                InvestigatePaymentWorkflow.run,
                payment,
                id="test-wf-004",
                task_queue="test-queue",
            )
    assert result.decision == Decision.APPROVE
    assert len(result.agent_results) == 4
