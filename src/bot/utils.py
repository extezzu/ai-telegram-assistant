"""Text processing utilities for Telegram messages."""

TELEGRAM_MAX_LENGTH = 4096


def split_message(
    text: str, max_length: int = TELEGRAM_MAX_LENGTH
) -> list[str]:
    """Split text into chunks that fit Telegram's message size limit."""
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

    return chunks


def _find_split_point(text: str, max_length: int) -> int:
    """Find the best split position, preferring natural boundaries."""
    # Paragraph break
    pos = text.rfind("\n\n", 0, max_length)
    if pos > max_length // 2:
        return pos + 2

    # Newline
    pos = text.rfind("\n", 0, max_length)
    if pos > max_length // 2:
        return pos + 1

    # Sentence end
    for sep in (". ", "! ", "? "):
        pos = text.rfind(sep, 0, max_length)
        if pos > max_length // 2:
            return pos + len(sep)

    # Word boundary
    pos = text.rfind(" ", 0, max_length)
    if pos > max_length // 4:
        return pos + 1

    return max_length
