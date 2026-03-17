from llm.prompts import ADVERSE_MEDIA_SYSTEM, ADVERSE_MEDIA_USER, ADVERSE_MEDIA_PROMPT_VERSION, GET_ADVERSE_MEDIA_TOOL
from knowledge.database import get_adverse_media
from observability.logging import get_logger
from schemas.payment import Payment
from .base import BaseAgent

log = get_logger()


class AdverseMediaAgent(BaseAgent):
    name = "adverse_media"
    db_tools = [GET_ADVERSE_MEDIA_TOOL]
    prompt_version = ADVERSE_MEDIA_PROMPT_VERSION

    async def _invoke(self, payment: Payment) -> dict:
        log.info("llm_call", agent=self.name, prompt_version=ADVERSE_MEDIA_PROMPT_VERSION)
        return await self._run_tool_loop([
            {"role": "system", "content": ADVERSE_MEDIA_SYSTEM},
            {"role": "user", "content": ADVERSE_MEDIA_USER.format(
                recipient_name=payment.recipient.name,
                recipient_account=payment.recipient.account_id,
                amount=payment.amount,
                currency=payment.currency,
            )},
        ], payment_id=payment.payment_id)

    async def _execute_db_tool(self, tool_name: str, args: dict):
        if tool_name == "get_adverse_media":
            return get_adverse_media(args["account_id"])
        raise ValueError(f"Unknown tool: {tool_name}")
