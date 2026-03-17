from llm.prompts import PAYMENT_PATTERN_SYSTEM, PAYMENT_PATTERN_USER, PAYMENT_PATTERN_PROMPT_VERSION, GET_PAYMENT_HISTORY_TOOL
from knowledge.database import get_payment_history
from observability.logging import get_logger
from schemas.payment import Payment
from .base import BaseAgent

log = get_logger()


class PaymentPatternAgent(BaseAgent):
    name = "payment_pattern"
    db_tools = [GET_PAYMENT_HISTORY_TOOL]
    prompt_version = PAYMENT_PATTERN_PROMPT_VERSION

    async def _invoke(self, payment: Payment) -> dict:
        log.info("llm_call", agent=self.name, prompt_version=PAYMENT_PATTERN_PROMPT_VERSION)
        return await self._run_tool_loop([
            {"role": "system", "content": PAYMENT_PATTERN_SYSTEM},
            {"role": "user", "content": PAYMENT_PATTERN_USER.format(
                recipient_name=payment.recipient.name,
                recipient_account=payment.recipient.account_id,
                amount=payment.amount,
                currency=payment.currency,
            )},
        ], payment_id=payment.payment_id)

    async def _execute_db_tool(self, tool_name: str, args: dict):
        if tool_name == "get_payment_history":
            return get_payment_history(args["account_id"])
        raise ValueError(f"Unknown tool: {tool_name}")
