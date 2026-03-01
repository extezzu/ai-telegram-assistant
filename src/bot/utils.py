"""Utility functions for text processing."""

import logging

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit.

    Splits on paragraph boundaries first, then sentence boundaries,
    then falls back to hard splitting at max_length.

    Args:
        text: The text to split.
        max_length: Maximum length per chunk.

    Returns:
        List of text chunks, each within max_length.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        split_pos = _find_split_point(remaining, max_length)
        chunks.append(remaining[:split_pos].rstrip())
        remaining = remaining[split_pos:].lstrip()

    logger.debug("Split message into %d chunks", len(chunks))
    return chunks


def _find_split_point(text: str, max_length: int) -> int:
    """Find the best position to split text.

    Tries paragraph break, then newline, then sentence end, then space.

    Args:
        text: Text to find split point in.
        max_length: Maximum position for the split.

    Returns:
        Position to split at.
    """
    # Try paragraph break
    pos = text.rfind("\n\n", 0, max_length)
    if pos > max_length // 2:
        return pos + 2

    # Try newline
    pos = text.rfind("\n", 0, max_length)
    if pos > max_length // 2:
        return pos + 1

    # Try sentence end
    for sep in (". ", "! ", "? "):
        pos = text.rfind(sep, 0, max_length)
        if pos > max_length // 2:
            return pos + len(sep)

    # Try space
    pos = text.rfind(" ", 0, max_length)
    if pos > max_length // 4:
        return pos + 1

    # Hard split
    return max_length


def escape_markdown(text: str) -> str:
    """Escape special Markdown V2 characters for Telegram.

    Args:
        text: Raw text to escape.

    Returns:
        Escaped text safe for MarkdownV2 parse mode.
    """
    special_chars = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for char in text:
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
    return escaped


def format_token_usage(
    prompt_tokens: int, completion_tokens: int, total_tokens: int
) -> str:
    """Format token usage stats as a readable string.

    Args:
        prompt_tokens: Number of prompt tokens used.
        completion_tokens: Number of completion tokens used.
        total_tokens: Total tokens used.

    Returns:
        Formatted string with token counts.
    """
    return (
        f"Tokens used — prompt: {prompt_tokens}, "
        f"completion: {completion_tokens}, "
        f"total: {total_tokens}"
    )
