from enum import Enum
from pydantic import BaseModel


class AgentType(str, Enum):
    COMPANY = "company"
    ADVERSE_MEDIA = "adverse_media"
    PAYMENT_PATTERN = "payment_pattern"
    SANCTIONS = "sanctions"


class OrchestratorPlan(BaseModel):
    agents_to_run: list[AgentType]
    reasoning: str
