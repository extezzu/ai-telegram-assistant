"""Tests for utility functions."""

from bot.utils import escape_markdown, format_token_usage, split_message


class TestSplitMessage:
    """Test message splitting logic."""

    def test_short_message_no_split(self) -> None:
        """Short messages should not be split."""
        text = "Hello, world!"
        result = split_message(text)
        assert result == ["Hello, world!"]

    def test_empty_message(self) -> None:
        """Empty message should return single empty string."""
        result = split_message("")
        assert result == [""]

    def test_exact_limit(self) -> None:
        """Message at exact limit should not be split."""
        text = "a" * 4096
        result = split_message(text, max_length=4096)
        assert len(result) == 1

    def test_split_on_paragraph(self) -> None:
        """Should prefer splitting on paragraph boundaries."""
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = f"{part1}\n\n{part2}"
        result = split_message(text, max_length=2500)
        assert len(result) == 2
        assert result[0] == part1
        assert result[1] == part2

    def test_split_on_newline(self) -> None:
        """Should split on newlines when no paragraph break."""
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = f"{part1}\n{part2}"
        result = split_message(text, max_length=2500)
        assert len(result) == 2

    def test_split_on_sentence(self) -> None:
        """Should split on sentence boundaries."""
        part1 = "a" * 2000 + "."
        part2 = "b" * 2000
        text = f"{part1} {part2}"
        result = split_message(text, max_length=2500)
        assert len(result) == 2

    def test_hard_split(self) -> None:
        """Should hard split when no good break point."""
        text = "a" * 5000
        result = split_message(text, max_length=2000)
        assert len(result) == 3
        assert all(len(chunk) <= 2000 for chunk in result)

    def test_multiple_splits(self) -> None:
        """Should handle multiple splits correctly."""
        text = "a" * 10000
        result = split_message(text, max_length=4096)
        assert len(result) == 3
        joined = "".join(result)
        assert joined == text


class TestEscapeMarkdown:
    """Test Markdown escaping."""

    def test_no_special_chars(self) -> None:
        """Plain text should not be modified."""
        assert escape_markdown("hello") == "hello"

    def test_escape_special_chars(self) -> None:
        """Special characters should be escaped."""
        assert escape_markdown("hello_world") == "hello\\_world"
        assert escape_markdown("*bold*") == "\\*bold\\*"
        assert escape_markdown("[link](url)") == "\\[link\\]\\(url\\)"


class TestFormatTokenUsage:
    """Test token usage formatting."""

    def test_format_output(self) -> None:
        """Should format token counts correctly."""
        result = format_token_usage(100, 50, 150)
        assert "100" in result
        assert "50" in result
        assert "150" in result
