"""Unit tests for CLI helper functions."""

from pathlib import Path
from unittest.mock import patch

import click
import pytest

from papertrail.__main__ import (
    collect_pdfs,
    in_date_range,
    is_missing_field,
    parse_date_range,
)


class TestCollectPdfs:
    """Tests for collect_pdfs."""

    def test_single_pdf_file(self, tmp_path: Path) -> None:
        pdf = tmp_path / "test.pdf"
        pdf.touch()
        assert collect_pdfs(pdf, recursive=False) == [pdf]

    def test_single_non_pdf_file(self, tmp_path: Path) -> None:
        txt = tmp_path / "test.txt"
        txt.touch()
        assert collect_pdfs(txt, recursive=False) == []

    def test_directory_non_recursive(self, tmp_path: Path) -> None:
        (tmp_path / "a.pdf").touch()
        (tmp_path / "b.pdf").touch()
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "c.pdf").touch()

        result = collect_pdfs(tmp_path, recursive=False)
        assert len(result) == 2
        assert all(p.parent == tmp_path for p in result)

    def test_directory_recursive(self, tmp_path: Path) -> None:
        (tmp_path / "a.pdf").touch()
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "b.pdf").touch()

        result = collect_pdfs(tmp_path, recursive=True)
        assert len(result) == 2

    def test_returns_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "z.pdf").touch()
        (tmp_path / "a.pdf").touch()
        (tmp_path / "m.pdf").touch()

        result = collect_pdfs(tmp_path, recursive=False)
        names = [p.name for p in result]
        assert names == ["a.pdf", "m.pdf", "z.pdf"]


class TestParseDateRange:
    """Tests for parse_date_range."""

    def test_valid_range(self) -> None:
        start, end = parse_date_range("2024-01-01..2024-12-31")
        assert start == "2024-01-01"
        assert end == "2024-12-31"

    def test_missing_separator(self) -> None:
        with pytest.raises(click.BadParameter, match="YYYY-MM-DD"):
            parse_date_range("2024-01-01")

    def test_invalid_start_format(self) -> None:
        with pytest.raises(click.BadParameter, match="YYYY-MM-DD"):
            parse_date_range("2024-1-01..2024-12-31")

    def test_invalid_end_format(self) -> None:
        with pytest.raises(click.BadParameter, match="YYYY-MM-DD"):
            parse_date_range("2024-01-01..24-12-31")

    def test_start_after_end(self) -> None:
        with pytest.raises(click.BadParameter, match="before"):
            parse_date_range("2024-12-31..2024-01-01")

    def test_same_date_valid(self) -> None:
        start, end = parse_date_range("2024-06-15..2024-06-15")
        assert start == end == "2024-06-15"


class TestInDateRange:
    """Tests for in_date_range."""

    def test_path_in_range(self) -> None:
        path = Path("/storage/2024/03/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is True

    def test_path_before_range(self) -> None:
        path = Path("/storage/2023/12/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is False

    def test_path_after_range(self) -> None:
        path = Path("/storage/2025/01/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is False

    def test_month_granularity(self) -> None:
        # File in 2024/03/ matches because 2024-03-01 <= 2024-03-15
        path = Path("/storage/2024/03/doc.pdf")
        assert in_date_range(path, "2024-03-15", "2024-03-31") is False
        # But matches if start includes first of month
        assert in_date_range(path, "2024-03-01", "2024-03-31") is True

    def test_no_date_in_path(self) -> None:
        path = Path("/some/random/path/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is False

    def test_boundary_start(self) -> None:
        path = Path("/storage/2024/01/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is True

    def test_boundary_end(self) -> None:
        path = Path("/storage/2024/12/doc.pdf")
        assert in_date_range(path, "2024-01-01", "2024-12-31") is True


class TestIsMissingField:
    """Tests for is_missing_field."""

    def test_no_sidecar(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        assert is_missing_field(pdf, "steuerrelevant") is True

    def test_field_present(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("title: Test\nsteuerrelevant: true\n")
        assert is_missing_field(pdf, "steuerrelevant") is False

    def test_field_missing(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("title: Test\n")
        assert is_missing_field(pdf, "steuerrelevant") is True

    def test_field_null(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("title: Test\nsteuerrelevant: null\n")
        assert is_missing_field(pdf, "steuerrelevant") is True

    def test_field_false_not_missing(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("title: Test\nsteuerrelevant: false\n")
        assert is_missing_field(pdf, "steuerrelevant") is False

    def test_invalid_yaml_returns_true(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("not: valid: yaml: {{{\n")
        with patch("papertrail.__main__.logger") as mock_logger:
            assert is_missing_field(pdf, "steuerrelevant") is True
            mock_logger.warning.assert_called_once()

    def test_empty_yaml_returns_true(self, tmp_path: Path) -> None:
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        sidecar = tmp_path / "doc.yaml"
        sidecar.write_text("")
        assert is_missing_field(pdf, "steuerrelevant") is True
