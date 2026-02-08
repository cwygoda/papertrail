"""Shared test fixtures."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from papertrail.domain.models import DocumentInfo
from papertrail.ports.llm import LLMPort
from papertrail.ports.metadata import MetadataPort
from papertrail.ports.ocr import OCRPort
from papertrail.ports.storage import StoragePort


@pytest.fixture
def sample_document_info() -> DocumentInfo:
    """Sample document info for testing."""
    return DocumentInfo(
        title="Invoice 12345",
        subject="Monthly subscription",
        issuer="Acme Corp",
        summary="Invoice for monthly subscription service",
        date=date(2024, 3, 15),
    )


@pytest.fixture
def mock_ocr() -> MagicMock:
    """Mock OCR port."""
    mock = MagicMock(spec=OCRPort)
    mock.extract_text.return_value = "Sample document text content."
    return mock


@pytest.fixture
def mock_llm(sample_document_info: DocumentInfo) -> MagicMock:
    """Mock LLM port."""
    mock = MagicMock(spec=LLMPort)
    mock.analyze.return_value = sample_document_info
    return mock


@pytest.fixture
def mock_metadata() -> MagicMock:
    """Mock metadata port."""
    mock = MagicMock(spec=MetadataPort)
    mock.write_sidecar.return_value = Path("/tmp/test.xmp")
    return mock


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock storage port."""
    mock = MagicMock(spec=StoragePort)
    mock.store.return_value = Path("/storage/2024/03/Invoice 12345 - 2024-03-15.pdf")
    mock.store_sidecar.return_value = Path(
        "/storage/2024/03/Invoice 12345 - 2024-03-15.xmp"
    )
    return mock
