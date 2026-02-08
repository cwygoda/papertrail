"""Unit tests for LLM validation module."""

import pytest

from papertrail.adapters.llm.validation import (
    DOC_BEGIN,
    DOC_END,
    looks_suspicious,
    sanitize_field,
)


class TestLooksSuspicious:
    """Tests for looks_suspicious function."""

    def test_empty_string_not_suspicious(self) -> None:
        assert looks_suspicious("") is False

    def test_none_not_suspicious(self) -> None:
        assert looks_suspicious(None) is False  # type: ignore[arg-type]

    def test_normal_text_not_suspicious(self) -> None:
        assert looks_suspicious("Invoice from Acme Corp") is False

    def test_path_traversal_suspicious(self) -> None:
        assert looks_suspicious("../../../etc/passwd") is True
        assert looks_suspicious("foo/../bar") is True

    def test_curly_braces_suspicious(self) -> None:
        assert looks_suspicious("function() { return x; }") is True

    def test_angle_brackets_suspicious(self) -> None:
        assert looks_suspicious("<script>alert('xss')</script>") is True

    def test_backticks_suspicious(self) -> None:
        assert looks_suspicious("`rm -rf /`") is True

    def test_control_chars_suspicious(self) -> None:
        assert looks_suspicious("normal\x00text") is True
        assert looks_suspicious("normal\x1ftext") is True

    def test_mixed_content_suspicious(self) -> None:
        assert looks_suspicious("Title with ../traversal") is True


class TestSanitizeField:
    """Tests for sanitize_field function."""

    def test_returns_text_when_safe(self) -> None:
        assert sanitize_field("Invoice 12345", "fallback") == "Invoice 12345"

    def test_returns_fallback_when_none(self) -> None:
        assert sanitize_field(None, "fallback") == "fallback"

    def test_returns_fallback_when_empty(self) -> None:
        assert sanitize_field("", "fallback") == "fallback"

    def test_returns_fallback_when_suspicious(self) -> None:
        assert sanitize_field("../evil", "fallback") == "fallback"
        assert sanitize_field("<script>", "fallback") == "fallback"

    def test_preserves_special_characters_when_safe(self) -> None:
        text = "Invoice #123 - Acme Corp (2024)"
        assert sanitize_field(text, "fallback") == text


class TestDelimiters:
    """Tests for document delimiters."""

    def test_delimiters_defined(self) -> None:
        assert DOC_BEGIN == "<<<DOCUMENT_TEXT_BEGIN>>>"
        assert DOC_END == "<<<DOCUMENT_TEXT_END>>>"
