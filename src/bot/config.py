"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    # Telegram
    telegram_bot_token: str

    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.7

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Conversation
    max_conversation_length: int = 20

    # Rate limiting
    rate_limit_per_minute: int = 10

    # System prompt
    default_system_prompt: str = (
        "You are a helpful AI assistant. Be concise and informative."
    )

    # Health check
    health_check_port: int = 8080

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Create and return settings instance."""
    return Settings()
