"""OCR port - interface for OCR processing."""

from abc import ABC, abstractmethod
from pathlib import Path


class OCRPort(ABC):
    """Interface for OCR processing."""

    @abstractmethod
    def process(self, path: Path) -> Path:
        """Run OCR on a PDF file, modifying in place.

        Returns path to processed file.
        """
        pass

    @abstractmethod
    def extract_text(self, path: Path) -> str:
        """Extract text content from PDF."""
        pass
