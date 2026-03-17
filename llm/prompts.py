"""Versioned prompt templates and tool schemas."""

PLANNER_PROMPT_VERSION = "planner_v2"
COMPANY_PROMPT_VERSION = "company_v4"
ADVERSE_MEDIA_PROMPT_VERSION = "adverse_media_v5"
PAYMENT_PATTERN_PROMPT_VERSION = "payment_pattern_v4"
SANCTIONS_PROMPT_VERSION = "sanctions_v4"

# ---------------------------------------------------------------------------
# response_format schema — used for all final risk assessments
# ---------------------------------------------------------------------------

RISK_ASSESSMENT_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "risk_assessment",
        "schema": {
            "type": "object",
            "properties": {
                "risk_signal": {
                    "type": "string",
                    "enum": ["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
                },
                "confidence": {"type": "number"},
                "evidence_summary": {"type": "string"},
                "reasoning": {"type": "string"},
            },
            "required": ["risk_signal", "confidence", "evidence_summary", "reasoning"],
        },
    },
}

# ---------------------------------------------------------------------------
# DB lookup tool schemas — one per agent type (information boundary)
# ---------------------------------------------------------------------------

GET_COMPANY_DATA_TOOL = {
    "type": "function",
    "function": {
        "name": "get_company_data",
        "description": "Look up company registry information for a recipient by account ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The recipient's bank account ID.",
                },
            },
            "required": ["account_id"],
        },
    },
}

GET_ADVERSE_MEDIA_TOOL = {
    "type": "function",
    "function": {
        "name": "get_adverse_media",
        "description": "Search for adverse media records (news articles, scam reports) about a recipient.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The recipient's bank account ID.",
                },
            },
            "required": ["account_id"],
        },
    },
}

GET_PAYMENT_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_payment_history",
        "description": "Retrieve historical payment transaction data for a recipient account.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The recipient's bank account ID.",
                },
            },
            "required": ["account_id"],
        },
    },
}

GET_SANCTIONS_DATA_TOOL = {
    "type": "function",
    "function": {
        "name": "get_sanctions_data",
        "description": "Screen a recipient against sanctions lists and PEP (Politically Exposed Person) databases.",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "The recipient's bank account ID.",
                },
                "name": {
                    "type": "string",
                    "description": "The recipient's full name for name-based screening.",
                },
            },
            "required": ["account_id", "name"],
        },
    },
}

# ---------------------------------------------------------------------------
# Planner tool schema
# ---------------------------------------------------------------------------

PLAN_INVESTIGATION_TOOL = {
    "type": "function",
    "function": {
        "name": "plan_investigation",
        "description": "Return the investigation plan specifying which specialist agents to run.",
        "parameters": {
            "type": "object",
            "properties": {
                "agents_to_run": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["company", "adverse_media", "payment_pattern", "sanctions"],
                    },
                    "description": "Agents to run. Always include sanctions.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why these agents were selected.",
                },
            },
            "required": ["agents_to_run", "reasoning"],
        },
    },
}

# ---------------------------------------------------------------------------
# Planner prompts
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = (
    "You are a payment risk orchestration planner for a financial compliance system. "
    "Given a payment, decide which specialist agents to run. "
    "Available agents: company, adverse_media, payment_pattern, sanctions. "
    "Always include sanctions."
)

PLANNER_USER = """Payment details:
- ID: {payment_id}
- Sender: {sender_name} ({sender_account})
- Recipient: {recipient_name} ({recipient_account})
- Amount: {amount} {currency}
- Reference: {reference}

Which specialist agents should investigate this payment?"""

# ---------------------------------------------------------------------------
# Agent system prompts — describe expertise and risk criteria only
# ---------------------------------------------------------------------------

COMPANY_SYSTEM = (
    "You are a company registry specialist for payment risk assessment. "
    "Use the get_company_data tool to retrieve company information, then assess risk. "
    "Risk criteria: dissolved/dormant status = HIGH; "
    "overdue filings = MEDIUM; "
    "incorporated strictly less than 12 months before the payment date = MEDIUM; "
    "active with up-to-date filings, incorporated 12+ months ago = LOW."
)

COMPANY_USER = (
    "Assess risk for a payment of {amount} {currency} to {recipient_name} "
    "(account: {recipient_account}). "
    "Look up their company registry data and produce a risk assessment."
)

ADVERSE_MEDIA_SYSTEM = (
    "You are an adverse media specialist for payment risk assessment. "
    "Use the get_adverse_media tool to retrieve news and scam reports, then assess risk. "
    "Base your signal strictly on the severity field and published_date in the retrieved records. "
    "Risk criteria: severity='high' AND published within the last 12 months = HIGH; "
    "any other hit (severity='medium', severity='low', or older than 12 months) = MEDIUM; "
    "no records found = LOW."
)

ADVERSE_MEDIA_USER = (
    "Assess risk for a payment of {amount} {currency} to {recipient_name} "
    "(account: {recipient_account}). "
    "Search for adverse media records and produce a risk assessment."
)

PAYMENT_PATTERN_SYSTEM = (
    "You are a payment pattern analyst for financial risk assessment. "
    "Use the get_payment_history tool to retrieve transaction data, then assess risk. "
    "Risk criteria: flagged_count > 3 = HIGH; "
    "flagged_count > 0 AND current payment amount > 2x avg_amount_gbp = MEDIUM; "
    "flagged_count = 0 = LOW regardless of payment size — a larger-than-usual payment to a clean recipient is not a risk signal; "
    "no history = UNKNOWN."
)

PAYMENT_PATTERN_USER = (
    "Assess risk for a payment of {amount} {currency} to {recipient_name} "
    "(account: {recipient_account}). "
    "Retrieve their payment history and assess whether this payment fits normal patterns."
)

SANCTIONS_SYSTEM = (
    "You are a sanctions and PEP screening specialist. This is a CRITICAL compliance check. "
    "Use the get_sanctions_data tool to screen the recipient. "
    "Risk criteria: "
    "actual sanctions list match (OFAC, UN, EU, etc.) = HIGH — this is a legal prohibition; "
    "PEP (politically exposed person) match only = MEDIUM — requires enhanced due diligence, not prohibited; "
    "no match = LOW."
)

SANCTIONS_USER = (
    "Screen the recipient of a payment of {amount} {currency}: {recipient_name} "
    "(account: {recipient_account}). "
    "Run a sanctions and PEP check and produce a risk assessment."
)
