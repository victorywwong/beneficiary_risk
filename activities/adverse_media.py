from temporalio import activity
from agents.adverse_media_agent import AdverseMediaAgent
from schemas.agent_result import AgentResult
from schemas.payment import Payment


@activity.defn
async def run_adverse_media_agent(payment: Payment) -> AgentResult:
    return await AdverseMediaAgent().run(payment)
