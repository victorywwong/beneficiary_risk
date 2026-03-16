from temporalio import activity
from agents.company_agent import CompanyAgent
from schemas.agent_result import AgentResult
from schemas.payment import Payment


@activity.defn
async def run_company_agent(payment: Payment) -> AgentResult:
    return await CompanyAgent().run(payment)
