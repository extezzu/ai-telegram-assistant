"""OpenAI GPT API client wrapper."""

import logging
from dataclasses import dataclass

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, RateLimitError

from bot.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AIClient:
    """Async wrapper around the OpenAI chat completions API."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._max_tokens = settings.openai_max_tokens
        self._temperature = settings.openai_temperature

    async def generate(
        self,
        messages: list[dict[str, str]],
    ) -> AIResponse:
        """Send messages to the OpenAI API and return the response."""
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
        except APITimeoutError:
            logger.error("OpenAI API request timed out")
            raise AIClientError("AI service timed out. Please try again.")
        except APIConnectionError:
            logger.error("Failed to connect to OpenAI API")
            raise AIClientError(
                "Could not connect to AI service. Please try again later."
            )
        except RateLimitError:
            logger.warning("OpenAI API rate limit exceeded")
            raise AIClientError(
                "AI service is busy. Please wait a moment and try again."
            )
        except Exception:
            logger.exception("Unexpected OpenAI API error")
            raise AIClientError(
                "An unexpected error occurred. Please try again later."
            )

        choice = response.choices[0]
        usage = response.usage

        logger.info(
            "Token usage — prompt: %d, completion: %d, total: %d",
            usage.prompt_tokens,
            usage.completion_tokens,
            usage.total_tokens,
        )

        return AIResponse(
            content=choice.message.content or "",
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    async def close(self) -> None:
        await self._client.close()


class AIClientError(Exception):
    """Raised when the AI client encounters an error."""
