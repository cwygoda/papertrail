"""Unit tests for filesystem storage adapter."""

import pytest

from papertrail.adapters.storage.filesystem import sanitize_filename


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_normal_filename_unchanged(self) -> None:
        assert sanitize_filename("Invoice 12345") == "Invoice 12345"

    def test_removes_null_bytes(self) -> None:
        assert sanitize_filename("test\x00file") == "testfile"

    def test_replaces_path_traversal(self) -> None:
        # ".." replaced with "_", "/" with "_", then collapsed
        assert sanitize_filename("../../../etc/passwd") == "etc passwd"
        assert sanitize_filename("foo..bar") == "foo bar"

    def test_replaces_problematic_chars(self) -> None:
        # All problem chars replaced with "_", then collapsed to single space
        assert sanitize_filename('file<>:"/\\|?*name') == "file name"

    def test_collapses_spaces_and_underscores(self) -> None:
        assert sanitize_filename("too   many   spaces") == "too many spaces"
        assert sanitize_filename("too___many___underscores") == "too many underscores"

    def test_strips_leading_trailing_dots_spaces(self) -> None:
        assert sanitize_filename("  .hidden  ") == "hidden"
        assert sanitize_filename("...dots...") == "dots"

    def test_returns_untitled_for_empty(self) -> None:
        assert sanitize_filename("") == "Untitled"
        assert sanitize_filename("   ") == "Untitled"
        assert sanitize_filename("...") == "Untitled"

    def test_truncates_long_names(self) -> None:
        long_name = "A" * 200
        result = sanitize_filename(long_name)
        assert len(result) <= 180

    def test_truncates_at_word_boundary(self) -> None:
        long_name = "Very " * 50  # 250 chars
        result = sanitize_filename(long_name)
        assert len(result) <= 180
        assert not result.endswith(" ")

    def test_custom_max_length(self) -> None:
        long_name = "A" * 100
        result = sanitize_filename(long_name, max_length=50)
        assert len(result) <= 50

    def test_unicode_preserved(self) -> None:
        assert sanitize_filename("Rechnung für März") == "Rechnung für März"
        assert sanitize_filename("日本語ファイル") == "日本語ファイル"
