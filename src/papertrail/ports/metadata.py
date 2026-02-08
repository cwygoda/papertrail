"""Metadata port - interface for PDF metadata and sidecar."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.models import DocumentInfo


class MetadataPort(ABC):
    """Interface for PDF metadata and sidecar handling."""

    @abstractmethod
    def update_pdf(self, path: Path, info: "DocumentInfo") -> None:
        """Update PDF metadata with extracted info."""
        pass

    @abstractmethod
    def write_sidecar(self, path: Path, info: "DocumentInfo") -> Path:
        """Write sidecar file alongside PDF.

        Returns path to sidecar file.
        """
        pass
