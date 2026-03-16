"""LLM-driven investigation planner activity."""
import json
from temporalio import activity
from llm.client import OpenRouterClient
from llm.prompts import PLANNER_SYSTEM, PLANNER_USER, PLANNER_PROMPT_VERSION, PLAN_INVESTIGATION_TOOL
from observability.logging import get_logger
from schemas.orchestrator_plan import AgentType, OrchestratorPlan
from schemas.payment import Payment

log = get_logger()

ALL_AGENTS = [AgentType.COMPANY, AgentType.ADVERSE_MEDIA, AgentType.PAYMENT_PATTERN, AgentType.SANCTIONS]


@activity.defn
async def plan_investigation(payment: Payment) -> OrchestratorPlan:
    log.info("planner_started", payment_id=payment.payment_id, prompt_version=PLANNER_PROMPT_VERSION)
    try:
        async with OpenRouterClient() as client:
            user_msg = PLANNER_USER.format(
                payment_id=payment.payment_id,
                sender_name=payment.sender.name,
                sender_account=payment.sender.account_id,
                recipient_name=payment.recipient.name,
                recipient_account=payment.recipient.account_id,
                amount=payment.amount,
                currency=payment.currency,
                reference=payment.reference,
            )
            msg = await client.complete(
                messages=[
                    {"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=256,
                tools=[PLAN_INVESTIGATION_TOOL],
                tool_choice={"type": "function", "function": {"name": "plan_investigation"}},
            )
            data = json.loads(msg.tool_calls[0].function.arguments)
            plan = OrchestratorPlan.model_validate(data)
            log.info("planner_completed", agents=plan.agents_to_run)
            return plan
    except Exception as e:
        log.warning("planner_fallback", error=str(e), payment_id=payment.payment_id)
        return OrchestratorPlan(
            agents_to_run=ALL_AGENTS,
            reasoning=f"Planner failed ({e}), falling back to all agents",
        )
