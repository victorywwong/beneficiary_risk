"""Async OpenRouter LLM client using the OpenAI-compatible SDK."""
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessage
from config import OPENROUTER_API_KEY, MODEL_ID

BASE_URL = "https://openrouter.ai/api/v1"


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
        key_preview = f"{OPENROUTER_API_KEY[:8]}..." if OPENROUTER_API_KEY else "NOT SET"
        tool_names = [t["function"]["name"] for t in tools] if tools else []
        print(
            f"[llm] endpoint={BASE_URL}/chat/completions "
            f"model={resolved_model} "
            f"key={key_preview} "
            f"tools={tool_names} "
            f"response_format={response_format.get('type') if response_format else None}",
            flush=True,
        )

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
        return response.choices[0].message

    async def close(self):
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()
