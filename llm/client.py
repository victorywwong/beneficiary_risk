"""Async OpenRouter LLM client using the OpenAI-compatible SDK.

Uses the Langfuse OpenAI wrapper when LANGFUSE_PUBLIC_KEY is configured,
automatically tracing every LLM call (messages, tool calls, token usage).
Falls back to the standard openai SDK when Langfuse is not configured.
"""
from openai.types.chat import ChatCompletionMessage
from config import OPENROUTER_API_KEY, MODEL_ID, LANGFUSE_PUBLIC_KEY
from observability.logging import get_logger

if LANGFUSE_PUBLIC_KEY:
    from langfuse.openai import AsyncOpenAI  # type: ignore[no-redef]
else:
    from openai import AsyncOpenAI

BASE_URL = "https://openrouter.ai/api/v1"

log = get_logger()


class OpenRouterClient:
    def __init__(self):
        self._client = AsyncOpenAI(
            base_url=BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )

    async def complete(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.0,
        model: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
    ) -> ChatCompletionMessage:
        """Single chat completion call. Returns the message object."""
        resolved_model = model or MODEL_ID
        kwargs: dict = dict(
            model=resolved_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)
        usage = response.usage
        log.info(
            "llm_response",
            model=resolved_model,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )
        return response.choices[0].message

    async def close(self):
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
