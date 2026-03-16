import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
MODEL_ID: str = os.getenv("MODEL_ID", "openai/gpt-4o-mini")
AGENT_TIMEOUT_SEC: int = int(os.getenv("AGENT_TIMEOUT_SEC", "30"))
MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "1"))
DB_PATH: str = os.getenv("DB_PATH", "knowledge/risk.db")
TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost:7233")
TASK_QUEUE: str = "risk-assessment"
