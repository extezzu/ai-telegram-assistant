"""Tests for the function-calling tools module."""

import json

import pytest

from bot.tools import TOOLS, dispatch_tool_call


class TestToolSchemas:

    def test_all_tools_have_required_fields(self):
        for tool in TOOLS:
            assert tool["type"] == "function"
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"

    def test_tool_names_are_unique(self):
        names = [tool["function"]["name"] for tool in TOOLS]
        assert len(names) == len(set(names))


class TestDispatchToolCall:

    @pytest.mark.asyncio
    async def test_lookup_order_returns_status(self):
        result_json = await dispatch_tool_call(
            "lookup_order", json.dumps({"order_id": "ord-9001"})
        )
        result = json.loads(result_json)
        assert result["order_id"] == "ORD-9001"
        assert result["status"] == "shipped"
        assert "tracking_number" in result

    @pytest.mark.asyncio
    async def test_lookup_order_missing_id(self):
        result_json = await dispatch_tool_call(
            "lookup_order", json.dumps({})
        )
        result = json.loads(result_json)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_reset_password_link_returns_url(self):
        result_json = await dispatch_tool_call(
            "reset_password_link",
            json.dumps({"email": "Alice@Example.COM"}),
        )
        result = json.loads(result_json)
        assert result["email"] == "alice@example.com"
        assert result["reset_url"].startswith("https://")
        assert result["expires_in_minutes"] == 30

    @pytest.mark.asyncio
    async def test_reset_password_link_invalid_email(self):
        result_json = await dispatch_tool_call(
            "reset_password_link", json.dumps({"email": "not-an-email"})
        )
        assert "error" in json.loads(result_json)

    @pytest.mark.asyncio
    async def test_escalate_to_human_creates_ticket(self):
        result_json = await dispatch_tool_call(
            "escalate_to_human",
            json.dumps(
                {"reason": "billing dispute", "priority": "high"}
            ),
        )
        result = json.loads(result_json)
        assert result["ticket_id"].startswith("TKT-")
        assert result["priority"] == "high"
        assert result["reason"] == "billing dispute"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        result_json = await dispatch_tool_call(
            "no_such_tool", json.dumps({})
        )
        assert "error" in json.loads(result_json)

    @pytest.mark.asyncio
    async def test_invalid_json_arguments(self):
        result_json = await dispatch_tool_call(
            "lookup_order", "{not-valid-json}"
        )
        assert "error" in json.loads(result_json)

    @pytest.mark.asyncio
    async def test_empty_arguments_string(self):
        result_json = await dispatch_tool_call("lookup_order", "")
        assert "error" in json.loads(result_json)
