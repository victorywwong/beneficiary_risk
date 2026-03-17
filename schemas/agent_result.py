from enum import Enum
from pydantic import BaseModel, Field


class RiskSignal(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class AgentResult(BaseModel):
    agent_name: str
    risk_signal: RiskSignal
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    reasoning: str
    is_available: bool = True
    error: str | None = None
    duration_ms: float = 0.0
    prompt_version: str | None = None
