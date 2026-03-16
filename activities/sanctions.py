from temporalio import activity
from agents.sanctions_agent import SanctionsAgent
from schemas.agent_result import AgentResult
from schemas.payment import Payment


@activity.defn
async def run_sanctions_agent(payment: Payment) -> AgentResult:
    return await SanctionsAgent().run(payment)
