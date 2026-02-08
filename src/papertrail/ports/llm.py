"""LLM port - interface for document analysis."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.models import DocumentInfo


class LLMPort(ABC):
    """Interface for LLM-based document analysis."""

    @abstractmethod
    def analyze(self, text: str) -> "DocumentInfo":
        """Analyze document text and extract metadata."""
        pass
