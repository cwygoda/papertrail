"""Domain services - orchestrate business logic."""

import logging
from pathlib import Path

from ..ports.llm import LLMPort
from ..ports.metadata import MetadataPort
from ..ports.ocr import OCRPort
from ..ports.storage import StoragePort
from .models import ProcessingResult

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrates document processing pipeline."""

    def __init__(
        self,
        ocr: OCRPort,
        llm: LLMPort,
        metadata: MetadataPort,
        storage: StoragePort,
        quarantine_dir: Path | None = None,
    ) -> None:
        self.ocr = ocr
        self.llm = llm
        self.metadata = metadata
        self.storage = storage
        self.quarantine_dir = quarantine_dir

    def process(self, path: Path, keep: bool = False) -> ProcessingResult:
        """Process a document through the full pipeline.

        Pipeline:
            1. OCR (if needed)
            2. Extract text
            3. LLM analysis
            4. Update PDF metadata
            5. Write sidecar
            6. Move to storage (unless keep=True)

        On failure: move to quarantine (if configured).
        """
        result = ProcessingResult(source_path=path)
        logger.info(f"Processing: {path.name}")

        if path.suffix.lower() != ".pdf":
            result.errors.append(f"Unsupported file type: {path.suffix}")
            self._quarantine_on_error(path, result)
            return result

        try:
            # 1. OCR
            self.ocr.process(path)

            # 2. Extract text
            text = self.ocr.extract_text(path)
            result.text_length = len(text)

            if not text.strip():
                result.errors.append("No text extracted from document")
                self._quarantine_on_error(path, result)
                return result

            # 3. LLM analysis
            info = self.llm.analyze(text)
            result.document_info = info

            # 4. Update PDF metadata
            self.metadata.update_pdf(path, info)

            # 5. Write sidecar
            yaml_sidecar = self.metadata.write_sidecar(path, info)
            txt_sidecar = path.with_suffix(".txt")

            # 6. Move to storage
            if not keep:
                result.output_path = self.storage.store(path, info)
                result.sidecar_path = self.storage.store_sidecar(
                    result.output_path, yaml_sidecar
                )
                if txt_sidecar.exists():
                    self.storage.store_sidecar(result.output_path, txt_sidecar)
                logger.info(f"Stored: {result.output_path}")
            else:
                result.output_path = path
                result.sidecar_path = yaml_sidecar
                logger.info("Kept in place (--keep)")

        except Exception as e:
            logger.exception(f"Processing failed: {e}")
            result.errors.append(str(e))
            self._quarantine_on_error(path, result)

        return result

    def _quarantine_on_error(self, path: Path, result: ProcessingResult) -> None:
        """Move file to quarantine if configured and processing failed."""
        if self.quarantine_dir and not result.success and path.exists():
            result.output_path = self.storage.quarantine(path, self.quarantine_dir)
            # Also quarantine any sidecars created
            for suffix in [".txt", ".yaml"]:
                sidecar = path.with_suffix(suffix)
                if sidecar.exists():
                    self.storage.quarantine(sidecar, self.quarantine_dir)
