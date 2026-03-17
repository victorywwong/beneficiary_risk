from llm.prompts import SANCTIONS_SYSTEM, SANCTIONS_USER, SANCTIONS_PROMPT_VERSION, GET_SANCTIONS_DATA_TOOL
from knowledge.database import get_sanctions_data
from observability.logging import get_logger
from schemas.payment import Payment
from .base import BaseAgent

log = get_logger()


class SanctionsAgent(BaseAgent):
    name = "sanctions"
    db_tools = [GET_SANCTIONS_DATA_TOOL]
    prompt_version = SANCTIONS_PROMPT_VERSION

    async def _invoke(self, payment: Payment) -> dict:
        log.info("llm_call", agent=self.name, prompt_version=SANCTIONS_PROMPT_VERSION)
        return await self._run_tool_loop([
            {"role": "system", "content": SANCTIONS_SYSTEM},
            {"role": "user", "content": SANCTIONS_USER.format(
                recipient_name=payment.recipient.name,
                recipient_account=payment.recipient.account_id,
                amount=payment.amount,
                currency=payment.currency,
            )},
        ], payment_id=payment.payment_id)

    async def _execute_db_tool(self, tool_name: str, args: dict):
        if tool_name == "get_sanctions_data":
            return get_sanctions_data(args["name"], args["account_id"])
        raise ValueError(f"Unknown tool: {tool_name}")
