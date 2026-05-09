"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables.

    The bot is provider-agnostic: any OpenAI-compatible API works
    (OpenAI, Groq, Together, OpenRouter, local Ollama, vLLM). Set
    `OPENAI_BASE_URL` to switch providers without code changes.
    """

    telegram_bot_token: str
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.7
    openai_base_url: str | None = None
    enable_function_calling: bool = False
    redis_url: str = "redis://localhost:6379/0"
    max_conversation_length: int = 20
    rate_limit_per_minute: int = 10
    default_system_prompt: str = (
        "You are a helpful AI assistant. Be concise and informative."
    )
    health_check_port: int = 8080
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    return Settings()
