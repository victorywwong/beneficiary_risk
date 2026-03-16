from temporalio import activity
from agents.payment_pattern_agent import PaymentPatternAgent
from schemas.agent_result import AgentResult
from schemas.payment import Payment


@activity.defn
async def run_payment_pattern_agent(payment: Payment) -> AgentResult:
    return await PaymentPatternAgent().run(payment)
