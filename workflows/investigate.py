"""Main Temporal workflow for payment risk investigation."""
import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities.planner import plan_investigation
    from activities.company import run_company_agent
    from activities.adverse_media import run_adverse_media_agent
    from activities.payment_pattern import run_payment_pattern_agent
    from activities.sanctions import run_sanctions_agent
    from orchestrator.synthesizer import synthesize
    from schemas.agent_result import AgentResult, RiskSignal
    from schemas.orchestrator_plan import AgentType, OrchestratorPlan
    from schemas.payment import Payment
    from schemas.risk_decision import Decision, RiskDecision


def make_failed_result(agent_name: str, error: Exception) -> AgentResult:
    return AgentResult(
        agent_name=agent_name,
        risk_signal=RiskSignal.UNKNOWN,
        confidence=0.0,
        evidence_summary="Activity failed",
        reasoning=str(error),
        is_available=False,
        error=str(error),
        duration_ms=0.0,
    )


AGENT_ACTIVITY_MAP = {
    AgentType.COMPANY: run_company_agent,
    AgentType.ADVERSE_MEDIA: run_adverse_media_agent,
    AgentType.PAYMENT_PATTERN: run_payment_pattern_agent,
    AgentType.SANCTIONS: run_sanctions_agent,
}


@workflow.defn
class InvestigatePaymentWorkflow:
    @workflow.run
    async def run(self, payment: Payment) -> RiskDecision:
        trace_id = str(workflow.uuid4())
        workflow.logger.info("investigation_started", extra={"payment_id": payment.payment_id, "trace_id": trace_id})

        # Step 1: LLM planner
        plan: OrchestratorPlan = await workflow.execute_activity(
            plan_investigation,
            payment,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        # Hard guardrail: always run sanctions
        if AgentType.SANCTIONS not in plan.agents_to_run:
            plan.agents_to_run.append(AgentType.SANCTIONS)

        # Step 2: Run agent activities in parallel
        agent_tasks = [
            workflow.execute_activity(
                AGENT_ACTIVITY_MAP[agent_type],
                payment,
                start_to_close_timeout=timedelta(seconds=40),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    non_retryable_error_types=["pydantic.ValidationError"],
                ),
            )
            for agent_type in plan.agents_to_run
        ]

        raw_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        # Step 3: Convert exceptions to failed AgentResult
        agent_results: list[AgentResult] = []
        for agent_type, result in zip(plan.agents_to_run, raw_results):
            if isinstance(result, Exception):
                agent_results.append(make_failed_result(agent_type.value, result))
            else:
                agent_results.append(result)

        # Step 4: Deterministic synthesis
        decision = synthesize(payment, plan, agent_results, trace_id)
        workflow.logger.info("decision_reached", extra={"decision": decision.decision, "payment_id": payment.payment_id})
        return decision
