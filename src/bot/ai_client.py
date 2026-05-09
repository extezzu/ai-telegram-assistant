"""OpenAI-compatible chat-completions client.

Works with any provider that exposes an OpenAI-compatible /v1/chat/completions
endpoint: OpenAI, Groq, Together, OpenRouter, DeepInfra, local Ollama, vLLM.
Switch providers via the `OPENAI_BASE_URL` env var.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError

from bot.config import Settings
from bot.tools import TOOLS, dispatch_tool_call

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    tool_calls_made: list[str] = field(default_factory=list)


class AIClient:
    """Async wrapper around the OpenAI-compatible chat completions API."""

    def __init__(self, settings: Settings) -> None:
        client_kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url

        self._client = AsyncOpenAI(**client_kwargs)
        self._model = settings.openai_model
        self._max_tokens = settings.openai_max_tokens
        self._temperature = settings.openai_temperature
        self._tools_enabled = settings.enable_function_calling

    async def generate(
        self,
        messages: list[dict[str, Any]],
    ) -> AIResponse:
        """Send messages to the chat-completions API and return the response.

        When function calling is enabled and the model requests tool execution,
        runs one round of tool dispatch and re-queries the model with the
        results before returning. Token counts are aggregated across calls.
        """
        if self._tools_enabled:
            return await self._generate_with_tools(messages)
        return await self._generate_plain(messages)

    async def _generate_plain(
        self, messages: list[dict[str, Any]]
    ) -> AIResponse:
        response = await self._call_api(messages, tools=None)
        return self._build_response(
            content=response.choices[0].message.content or "",
            usage=response.usage,
            tool_calls_made=[],
        )

    async def _generate_with_tools(
        self, messages: list[dict[str, Any]]
    ) -> AIResponse:
        first = await self._call_api(messages, tools=TOOLS)
        message = first.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            return self._build_response(
                content=message.content or "",
                usage=first.usage,
                tool_calls_made=[],
            )

        followup_messages: list[dict[str, Any]] = [
            *messages,
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            },
        ]

        names_invoked: list[str] = []
        for tc in tool_calls:
            names_invoked.append(tc.function.name)
            result = await dispatch_tool_call(
                tc.function.name, tc.function.arguments
            )
            followup_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

        second = await self._call_api(followup_messages, tools=None)

        prompt_tokens = first.usage.prompt_tokens + second.usage.prompt_tokens
        completion_tokens = (
            first.usage.completion_tokens + second.usage.completion_tokens
        )
        total_tokens = first.usage.total_tokens + second.usage.total_tokens

        return AIResponse(
            content=second.choices[0].message.content or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            tool_calls_made=names_invoked,
        )

    async def _call_api(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ):
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            return await self._client.chat.completions.create(**kwargs)
        except APITimeoutError:
            logger.error("AI API request timed out")
            raise AIClientError("AI service timed out. Please try again.")
        except APIConnectionError:
            logger.error("Failed to connect to AI API")
            raise AIClientError(
                "Could not connect to AI service. Please try again later."
            )
        except RateLimitError:
            logger.warning("AI API rate limit exceeded")
            raise AIClientError(
                "AI service is busy. Please wait a moment and try again."
            )
        except Exception:
            logger.exception("Unexpected AI API error")
            raise AIClientError(
                "An unexpected error occurred. Please try again later."
            )

    def _build_response(
        self,
        content: str,
        usage: Any,
        tool_calls_made: list[str],
    ) -> AIResponse:
        logger.info(
            "Token usage — prompt: %d, completion: %d, total: %d, tools: %s",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
            tool_calls_made or "none",
        )
        return AIResponse(
            content=content,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            tool_calls_made=tool_calls_made,
        )

    async def close(self) -> None:
        await self._client.close()


class AIClientError(Exception):
    """Raised when the AI client encounters an error."""
