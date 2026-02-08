"""Storage port - interface for file storage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.models import DocumentInfo


class StoragePort(ABC):
    """Interface for file storage."""

    @abstractmethod
    def store(self, path: Path, info: "DocumentInfo") -> Path:
        """Store a file with metadata-based naming.

        Returns path to stored file.
        """
        pass

    @abstractmethod
    def store_sidecar(self, pdf_path: Path, sidecar_path: Path) -> Path:
        """Store sidecar file alongside its PDF.

        Returns path to stored sidecar.
        """
        pass

    @abstractmethod
    def quarantine(self, path: Path, quarantine_dir: Path) -> Path:
        """Move file to quarantine.

        Returns path to quarantined file.
        """
        pass
