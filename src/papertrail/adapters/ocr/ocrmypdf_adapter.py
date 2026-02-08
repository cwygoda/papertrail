"""OCR adapter using ocrmypdf."""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from ...ports.ocr import OCRPort

logger = logging.getLogger(__name__)


class OcrMyPdfAdapter(OCRPort):
    """OCR implementation using ocrmypdf."""

    def process(self, path: Path) -> Path:
        logger.info(f"Running OCR: {path.name}")

        sidecar_path = path.with_suffix(".txt")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            subprocess.run(
                [
                    "ocrmypdf",
                    "--quiet",
                    "--force-ocr",
                    "--optimize", "1",
                    "--output-type", "pdfa",
                    "--sidecar", str(sidecar_path),
                    str(path),
                    str(tmp_path),
                ],
                check=True,
            )
            shutil.move(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        logger.info(f"OCR complete: {path.name} (PDF/A + sidecar)")
        return path

    def extract_text(self, path: Path) -> str:
        sidecar_path = path.with_suffix(".txt")
        if sidecar_path.exists():
            return sidecar_path.read_text()
        raise FileNotFoundError(f"Text sidecar not found: {sidecar_path}")
