"""Unit tests for domain models."""

from datetime import date
from pathlib import Path

from papertrail.domain.models import DocumentInfo, ProcessingResult


class TestProcessingResult:
    """Tests for ProcessingResult."""

    def test_success_when_no_errors_and_has_info(self) -> None:
        info = DocumentInfo(
            title="Test",
            subject="Test",
            issuer="Test",
            summary="Test",
            date=date.today(),
        )
        result = ProcessingResult(
            source_path=Path("/test.pdf"),
            document_info=info,
        )
        assert result.success is True

    def test_failure_when_has_errors(self) -> None:
        info = DocumentInfo(
            title="Test",
            subject="Test",
            issuer="Test",
            summary="Test",
            date=date.today(),
        )
        result = ProcessingResult(
            source_path=Path("/test.pdf"),
            document_info=info,
            errors=["Something failed"],
        )
        assert result.success is False

    def test_failure_when_no_document_info(self) -> None:
        result = ProcessingResult(
            source_path=Path("/test.pdf"),
            document_info=None,
        )
        assert result.success is False

    def test_failure_when_no_info_and_has_errors(self) -> None:
        result = ProcessingResult(
            source_path=Path("/test.pdf"),
            document_info=None,
            errors=["Failed to process"],
        )
        assert result.success is False

    def test_defaults(self) -> None:
        result = ProcessingResult(source_path=Path("/test.pdf"))
        assert result.document_info is None
        assert result.output_path is None
        assert result.sidecar_path is None
        assert result.text_length == 0
        assert result.errors == []


class TestDocumentInfo:
    """Tests for DocumentInfo."""

    def test_steuerrelevant_default_false(self) -> None:
        info = DocumentInfo(
            title="Test",
            subject="Test",
            issuer="Test",
            summary="Test",
            date=None,
        )
        assert info.steuerrelevant is False

    def test_steuerrelevant_can_be_true(self) -> None:
        info = DocumentInfo(
            title="Steuerbescheid 2024",
            subject="Steuern",
            issuer="Finanzamt",
            summary="Einkommensteuerbescheid",
            date=date(2024, 3, 15),
            steuerrelevant=True,
        )
        assert info.steuerrelevant is True
