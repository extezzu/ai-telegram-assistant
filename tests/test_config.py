"""Tests for configuration."""

import os
from unittest.mock import patch

import pytest

from bot.config import Settings, get_settings


class TestSettings:

    def test_required_fields(self, settings):
        assert settings.telegram_bot_token == "test-token"
        assert settings.openai_api_key == "test-key"

    def test_defaults(self, settings):
        assert settings.openai_model == "gpt-4o-mini"
        assert settings.openai_max_tokens == 100
        assert settings.openai_temperature == 0.7
        assert settings.max_conversation_length == 10
        assert settings.rate_limit_per_minute == 5

    def test_missing_required_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(Exception):
                Settings()

    def test_from_env(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "env-token",
            "OPENAI_API_KEY": "env-key",
        }
        with patch.dict(os.environ, env, clear=True):
            s = get_settings()
            assert s.telegram_bot_token == "env-token"
            assert s.openai_api_key == "env-key"
