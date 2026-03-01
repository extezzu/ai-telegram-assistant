"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from bot.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration."""

    def test_settings_with_required_fields(self, settings: Settings) -> None:
        """Settings should load with required fields."""
        assert settings.telegram_bot_token == "test-token"
        assert settings.openai_api_key == "test-key"

    def test_settings_defaults(self, settings: Settings) -> None:
        """Settings should have correct defaults."""
        assert settings.openai_model == "gpt-4o-mini"
        assert settings.openai_max_tokens == 100
        assert settings.openai_temperature == 0.7
        assert settings.max_conversation_length == 10
        assert settings.rate_limit_per_minute == 5

    def test_settings_missing_required_fields(self) -> None:
        """Settings should raise error when required fields are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                Settings()

    def test_get_settings_from_env(self) -> None:
        """get_settings should create Settings from environment."""
        env = {
            "TELEGRAM_BOT_TOKEN": "env-token",
            "OPENAI_API_KEY": "env-key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
            assert s.telegram_bot_token == "env-token"
            assert s.openai_api_key == "env-key"
