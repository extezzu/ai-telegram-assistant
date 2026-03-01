"""Tests for utility functions."""

from bot.utils import split_message


class TestSplitMessage:

    def test_short_message(self) -> None:
        assert split_message("Hello, world!") == ["Hello, world!"]

    def test_empty_message(self) -> None:
        assert split_message("") == [""]

    def test_exact_limit(self) -> None:
        text = "a" * 4096
        assert len(split_message(text, max_length=4096)) == 1

    def test_split_on_paragraph(self) -> None:
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = f"{part1}\n\n{part2}"
        result = split_message(text, max_length=2500)
        assert len(result) == 2
        assert result[0] == part1
        assert result[1] == part2

    def test_split_on_newline(self) -> None:
        part1 = "a" * 2000
        part2 = "b" * 2000
        text = f"{part1}\n{part2}"
        assert len(split_message(text, max_length=2500)) == 2

    def test_split_on_sentence(self) -> None:
        part1 = "a" * 2000 + "."
        part2 = "b" * 2000
        text = f"{part1} {part2}"
        assert len(split_message(text, max_length=2500)) == 2

    def test_hard_split(self) -> None:
        text = "a" * 5000
        result = split_message(text, max_length=2000)
        assert len(result) == 3
        assert all(len(chunk) <= 2000 for chunk in result)

    def test_multiple_splits(self) -> None:
        text = "a" * 10000
        result = split_message(text, max_length=4096)
        assert len(result) == 3
        assert "".join(result) == text
