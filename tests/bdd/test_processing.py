"""BDD step definitions for document processing."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from papertrail.domain.models import DocumentInfo, ProcessingResult
from papertrail.domain.services import ProcessingService
from papertrail.ports.llm import LLMPort
from papertrail.ports.metadata import MetadataPort
from papertrail.ports.ocr import OCRPort
from papertrail.ports.storage import StoragePort


@scenario("features/processing.feature", "Successful PDF processing")
def test_successful_processing() -> None:
    pass


@scenario("features/processing.feature", "Non-PDF file rejected")
def test_non_pdf_rejected() -> None:
    pass


@scenario("features/processing.feature", "Empty document quarantined")
def test_empty_document_quarantined() -> None:
    pass


@scenario("features/processing.feature", "Keep in place mode")
def test_keep_mode() -> None:
    pass


@pytest.fixture
def context(tmp_path: Path) -> dict:
    """Shared test context with temp directory."""
    return {"tmp_path": tmp_path}


@given("a processing service with mock adapters")
def setup_service(context: dict) -> None:
    context["ocr"] = MagicMock(spec=OCRPort)
    context["llm"] = MagicMock(spec=LLMPort)
    context["metadata"] = MagicMock(spec=MetadataPort)
    context["storage"] = MagicMock(spec=StoragePort)
    context["quarantine_dir"] = context["tmp_path"] / "quarantine"

    context["service"] = ProcessingService(
        ocr=context["ocr"],
        llm=context["llm"],
        metadata=context["metadata"],
        storage=context["storage"],
        quarantine_dir=context["quarantine_dir"],
    )


@given(parsers.parse('a PDF file at "{path}"'))
def given_pdf_file(context: dict, path: str) -> None:
    # Create actual file in tmp dir for path.exists() checks
    file_path = context["tmp_path"] / Path(path).name
    file_path.write_bytes(b"%PDF-1.4 test content")
    context["file_path"] = file_path


@given(parsers.parse('a file at "{path}"'))
def given_file(context: dict, path: str) -> None:
    # Create actual file in tmp dir for path.exists() checks
    file_path = context["tmp_path"] / Path(path).name
    file_path.write_bytes(b"test content")
    context["file_path"] = file_path


@given(parsers.parse('the OCR extracts text "{text}"'))
def ocr_extracts_text(context: dict, text: str) -> None:
    context["ocr"].extract_text.return_value = text


@given("the OCR extracts empty text")
def ocr_extracts_empty(context: dict) -> None:
    context["ocr"].extract_text.return_value = ""


@given("the LLM returns document info")
def llm_returns_info(context: dict) -> None:
    info = DocumentInfo(
        title="Invoice from Acme",
        subject="Payment",
        issuer="Acme Corp",
        summary="Monthly invoice",
        date=date(2024, 3, 15),
    )
    context["llm"].analyze.return_value = info
    context["metadata"].write_sidecar.return_value = Path("/tmp/test.yaml")
    context["storage"].store.return_value = Path("/storage/2024/03/Invoice.pdf")
    context["storage"].store_sidecar.return_value = Path(
        "/storage/2024/03/Invoice.yaml"
    )


@when("I process the document")
def process_document(context: dict) -> None:
    context["result"] = context["service"].process(context["file_path"])


@when("I process the document with keep mode")
def process_document_keep(context: dict) -> None:
    context["result"] = context["service"].process(context["file_path"], keep=True)


@then("the result should be successful")
def result_successful(context: dict) -> None:
    result: ProcessingResult = context["result"]
    assert result.success, f"Expected success, got errors: {result.errors}"


@then(parsers.parse('the result should have error "{error}"'))
def result_has_error(context: dict, error: str) -> None:
    result: ProcessingResult = context["result"]
    assert any(error in e for e in result.errors), (
        f"Expected error '{error}', got: {result.errors}"
    )


@then("the document should be stored")
def document_stored(context: dict) -> None:
    context["storage"].store.assert_called_once()


@then("a sidecar file should be created")
def sidecar_created(context: dict) -> None:
    context["metadata"].write_sidecar.assert_called_once()


@then("the file should be quarantined")
def file_quarantined(context: dict) -> None:
    context["storage"].quarantine.assert_called()


@then("the document should remain at the original path")
def document_at_original(context: dict) -> None:
    result: ProcessingResult = context["result"]
    assert result.output_path == context["file_path"]
    context["storage"].store.assert_not_called()
