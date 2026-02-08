"""LLM adapter using Claude API."""

import logging
from datetime import date

from ...domain.models import DocumentInfo
from ...ports.llm import LLMPort
from .prompts import SYSTEM_PROMPT
from .validation import DOC_BEGIN, DOC_END, looks_suspicious, sanitize_field

logger = logging.getLogger(__name__)


class ClaudeAPIAdapter(LLMPort):
    """LLM implementation using Claude API (pay-as-you-go)."""

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model

    def analyze(self, text: str) -> DocumentInfo:
        logger.info("Analyzing document with Claude API")

        if len(text) > 100_000:
            text = text[:100_000] + "\n\n[Truncated...]"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"{DOC_BEGIN}\n{text}\n{DOC_END}"},
            ],
        )

        block = response.content[0]
        text = block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]
        return self._parse_response(text)

    def _parse_response(self, text: str) -> DocumentInfo:
        import json

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
