"""OpenAI function-calling tools.

This module defines the tools the bot can invoke during a conversation. The
schemas follow the OpenAI tool-call spec (https://platform.openai.com/docs/guides/function-calling).

Three demo tools are wired up — `lookup_order`, `reset_password_link`, and
`escalate_to_human` — modeled on a SaaS customer-support scenario. Replace
the `_handle_*` bodies with calls into your own backend (REST API, internal
DB, CRM, ticketing system) to ship a production support bot.

Add a new tool in three steps:
    1. Append a JSON schema to `TOOLS`.
    2. Implement an async `_handle_<name>` coroutine.
    3. Register it in `_DISPATCH`.
"""

from __future__ import annotations

import json
import logging
import secrets
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": (
                "Look up the status of a customer order by its order ID. "
                "Use when the user asks about an order, shipment, or "
                "delivery status."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID, e.g. 'ORD-12345'.",
                    },
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_password_link",
            "description": (
                "Generate a password reset link for the user's account. "
                "Use when the user reports being locked out, forgot their "
                "password, or asks to reset credentials."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Account email address.",
                    },
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Escalate the conversation to a human support agent. Use "
                "when the user explicitly asks for a human, when the issue "
                "involves billing disputes, or when the bot cannot resolve "
                "the request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": (
                            "Short summary of why escalation is needed."
                        ),
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Ticket priority.",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


async def _handle_lookup_order(arguments: dict[str, Any]) -> dict[str, Any]:
    """Demo implementation. Replace with a call to your order-management API."""
    order_id = arguments.get("order_id", "").strip().upper()
    if not order_id:
        return {"error": "order_id is required"}

    # Replace this with: `await orders_api.get(order_id)`
    return {
        "order_id": order_id,
        "status": "shipped",
        "tracking_number": f"TRK-{order_id.split('-')[-1]}-DEMO",
        "estimated_delivery": "2-3 business days",
        "_note": "demo data — wire to your orders backend",
    }


async def _handle_reset_password_link(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Demo implementation. Replace with a call to your auth service."""
    email = arguments.get("email", "").strip().lower()
    if "@" not in email:
        return {"error": "valid email is required"}

    token = secrets.token_urlsafe(16)

    # Replace this with: `await auth_api.create_reset_token(email)`
    return {
        "email": email,
        "reset_url": f"https://example.com/reset?token={token}",
        "expires_in_minutes": 30,
        "_note": "demo data — wire to your auth backend",
    }


async def _handle_escalate_to_human(
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Demo implementation. Replace with a call to your ticketing system."""
    reason = arguments.get("reason", "no reason provided")
    priority = arguments.get("priority", "normal")

    # Replace this with: `await zendesk.create_ticket(...)` or similar.
    ticket_id = f"TKT-{secrets.token_hex(4).upper()}"
    return {
        "ticket_id": ticket_id,
        "status": "queued",
        "priority": priority,
        "reason": reason,
        "expected_response": "within 1 business hour",
        "_note": "demo data — wire to your ticketing backend",
    }


_DISPATCH: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "lookup_order": _handle_lookup_order,
    "reset_password_link": _handle_reset_password_link,
    "escalate_to_human": _handle_escalate_to_human,
}


async def dispatch_tool_call(name: str, arguments_json: str) -> str:
    """Execute a tool by name and return its JSON-serialized result."""
    handler = _DISPATCH.get(name)
    if handler is None:
        logger.warning("Unknown tool requested: %s", name)
        return json.dumps({"error": f"unknown tool: {name}"})

    try:
        arguments = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError:
        logger.exception("Tool %s received invalid JSON arguments", name)
        return json.dumps({"error": "invalid arguments"})

    try:
        result = await handler(arguments)
    except Exception:
        logger.exception("Tool %s raised an exception", name)
        return json.dumps({"error": "tool execution failed"})

    return json.dumps(result)
