"""LLM adapter using Ollama."""

import json
import logging
from datetime import date
from urllib.parse import urlparse

import httpx

from ...domain.models import DocumentInfo
from ...ports.llm import LLMPort
from .prompts import SYSTEM_PROMPT
from .validation import DOC_BEGIN, DOC_END, looks_suspicious, sanitize_field

logger = logging.getLogger(__name__)


class OllamaAdapter(LLMPort):
    """LLM implementation using Ollama."""

    def __init__(
        self,
        model: str = "gemma3:4b",
        base_url: str = "http://localhost:11434",
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid ollama_url scheme: {parsed.scheme}")
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze(self, text: str) -> DocumentInfo:
        logger.info(f"Analyzing document with Ollama ({self.model})")

        if len(text) > 100_000:
            text = text[:100_000] + "\n\n[Truncated...]"

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{DOC_BEGIN}\n{text}\n{DOC_END}"},
                ],
                "stream": False,
                "format": "json",
            },
            timeout=120.0,
        )
        response.raise_for_status()

        content = response.json()["message"]["content"]
        return self._parse_response(content)

    def _parse_response(self, text: str) -> DocumentInfo:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON response: {text[:200]}")
            return DocumentInfo(
                title="Untitled",
                subject="",
                issuer="Unknown",
                summary="",
                date=None,
            )

        # Parse date
        doc_date = None
        date_str = data.get("date")
        if date_str and date_str.lower() not in ("null", "unknown", "none"):
            try:
                doc_date = date.fromisoformat(date_str)
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")

        title = sanitize_field(data.get("title"), "Untitled")
        subject = sanitize_field(data.get("subject"), "")
        issuer = sanitize_field(data.get("issuer"), "Unknown")

        if looks_suspicious(data.get("title", "")):
            logger.warning(f"Suspicious title rejected: {data.get('title', '')[:50]}")

        return DocumentInfo(
            title=title,
            subject=subject,
            issuer=issuer,
            summary=data.get("summary", ""),  # Allow free-form text
            date=doc_date,
            steuerrelevant=bool(data.get("steuerrelevant", False)),
        )
