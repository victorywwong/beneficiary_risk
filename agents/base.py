"""Base agent: agentic DB-lookup loop then structured risk assessment."""
import asyncio
import json
import time
from abc import ABC, abstractmethod

from llm.client import OpenRouterClient
from llm.prompts import RISK_ASSESSMENT_RESPONSE_FORMAT
from observability.logging import get_logger
from schemas.agent_result import AgentResult, RiskSignal
from schemas.payment import Payment

log = get_logger()

MAX_TOOL_ITERATIONS = 5


class BaseAgent(ABC):
    name: str
    timeout_sec: float = 30.0
    db_tools: list[dict] = []  # DB lookup tools — scoped per agent

    def __init__(self):
        self.client = OpenRouterClient()

    async def run(self, payment: Payment) -> AgentResult:
        start = time.monotonic()
        try:
            data = await asyncio.wait_for(
                self._invoke(payment), timeout=self.timeout_sec
            )
            data["agent_name"] = self.name
            result = AgentResult.model_validate(data)
            result.duration_ms = (time.monotonic() - start) * 1000
            log.info(
                "agent_completed",
                agent=self.name,
                risk_signal=result.risk_signal,
                confidence=result.confidence,
                duration_ms=result.duration_ms,
            )
            return result
        except asyncio.TimeoutError:
            duration_ms = (time.monotonic() - start) * 1000
            log.warning("agent_failed", agent=self.name, error="timeout", duration_ms=duration_ms)
            return AgentResult(
                agent_name=self.name,
                risk_signal=RiskSignal.UNKNOWN,
                confidence=0.0,
                evidence_summary="Agent timed out",
                reasoning="Request exceeded timeout limit",
                is_available=False,
                error="timeout",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            log.error("agent_failed", agent=self.name, error=str(e), duration_ms=duration_ms)
            return AgentResult(
                agent_name=self.name,
                risk_signal=RiskSignal.UNKNOWN,
                confidence=0.0,
                evidence_summary="Agent encountered an error",
                reasoning=str(e),
                is_available=False,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def _run_tool_loop(self, messages: list[dict]) -> dict:
        """
        Agentic loop: call LLM with DB tools + response_format on every turn.
        Model calls tools to fetch data; when done it returns structured JSON.
        """
        for _ in range(MAX_TOOL_ITERATIONS):
            msg = await self.client.complete(
                messages,
                tools=self.db_tools,
                tool_choice="auto",
                max_tokens=512,
                response_format=RISK_ASSESSMENT_RESPONSE_FORMAT,
            )

            if not msg.tool_calls:
                # Model chose to respond with structured JSON — we're done
                return json.loads(msg.content)

            # Append assistant message (tool calls) to history
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each DB tool call and append results
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await self._execute_db_tool(tc.function.name, args)
                log.info("tool_result", agent=self.name, tool=tc.function.name)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        raise RuntimeError(f"Agent {self.name} exceeded {MAX_TOOL_ITERATIONS} tool iterations")

    @abstractmethod
    async def _invoke(self, payment: Payment) -> dict: ...

    @abstractmethod
    async def _execute_db_tool(self, tool_name: str, args: dict): ...
