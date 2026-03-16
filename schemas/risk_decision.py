from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from schemas.agent_result import AgentResult, RiskSignal


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class RiskDecision(BaseModel):
    payment_id: str
    decision: Decision
    aggregate_risk: RiskSignal
    confidence: float
    agent_results: list[AgentResult]
    reasoning: str
    trace_id: str
    investigated_at: datetime
