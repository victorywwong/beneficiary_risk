"""Tests for agent tool-loop, timeout, and error handling."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from schemas.payment import Payment, Sender, Recipient
from schemas.agent_result import AgentResult, RiskSignal
from agents.company_agent import CompanyAgent


@pytest.fixture
def payment():
    return Payment(
        payment_id="pay_test",
        sender=Sender(name="Test Sender", account_id="SENDER001", bank="Test Bank"),
        recipient=Recipient(name="Test Recipient", account_id="RECV001", bank="Test Bank"),
        amount=10000.0,
        currency="GBP",
        reference="Test payment",
        timestamp=datetime.now(timezone.utc),
    )


def _make_tool_call_msg(tool_name: str, args: dict) -> MagicMock:
    """Simulate an assistant message that calls a tool."""
    tc = MagicMock()
    tc.id = "call_abc"
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    return msg


def _make_text_msg(content: str) -> MagicMock:
    """Simulate a final assistant message with text content (response_format)."""
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = content
    return msg


FINAL_ASSESSMENT = json.dumps({
    "risk_signal": "LOW",
    "confidence": 0.85,
    "evidence_summary": "Company is active with up-to-date filings",
    "reasoning": "No risk indicators found",
})

COMPANY_DATA = {"name": "Test Corp", "status": "active", "filing_status": "up_to_date"}


async def test_company_agent_tool_loop_and_structured_output(payment):
    """Agent calls get_company_data tool, then produces structured assessment."""
    with patch("agents.base.OpenRouterClient") as mock_cls:
        mock_client = AsyncMock()
        # First call: model requests DB lookup
        # Second call: structured assessment (response_format)
        mock_client.complete = AsyncMock(side_effect=[
            _make_tool_call_msg("get_company_data", {"account_id": "RECV001"}),
            _make_text_msg(FINAL_ASSESSMENT),
        ])
        mock_cls.return_value = mock_client

        with patch("agents.company_agent.get_company_data", return_value=COMPANY_DATA):
            agent = CompanyAgent()
            agent.client = mock_client
            result = await agent.run(payment)

    assert isinstance(result, AgentResult)
    assert result.risk_signal == RiskSignal.LOW
    assert result.confidence == 0.85
    assert result.is_available is True
    assert result.agent_name == "company"
    # Verify the tool was called (two complete() calls: tool loop + final)
    assert mock_client.complete.call_count == 2


async def test_agent_timeout_returns_unavailable(payment):
    with patch("agents.base.OpenRouterClient"):
        agent = CompanyAgent()
        agent.timeout_sec = 0.001

        async def slow_invoke(*_):
            await asyncio.sleep(10)

        agent._invoke = slow_invoke
        result = await agent.run(payment)

    assert result.is_available is False
    assert result.error == "timeout"
    assert result.risk_signal == RiskSignal.UNKNOWN


async def test_agent_exception_returns_unavailable(payment):
    with patch("agents.base.OpenRouterClient"):
        agent = CompanyAgent()

        async def failing_invoke(*_):
            raise RuntimeError("Network error")

        agent._invoke = failing_invoke
        result = await agent.run(payment)

    assert result.is_available is False
    assert "Network error" in result.error
