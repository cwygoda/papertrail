"""Domain models."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class DocumentInfo:
    """Extracted document metadata."""

    title: str
    subject: str
    issuer: str
    summary: str
    date: date | None  # Issue/document date
    steuerrelevant: bool = False  # Relevant for German tax declaration


@dataclass
class ProcessingResult:
    """Result of document processing."""

    source_path: Path
    document_info: DocumentInfo | None = None
    output_path: Path | None = None
    sidecar_path: Path | None = None
    text_length: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0 and self.document_info is not None
