"""LLM adapter using Claude API."""

import logging
from datetime import date

from ...domain.models import DocumentInfo
from ...ports.llm import LLMPort

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a document analyzer. Extract metadata from the provided document text.

Respond in exactly this format (no markdown, no extra text):
TITLE: <document title or descriptive name>
SUBJECT: <main topic/category>
AUTHOR: <who wrote/sent/issued the document, or "Unknown" if not clear>
DATE: <document/issue date in YYYY-MM-DD format, or "Unknown" if not found>
SUMMARY: <2-3 sentence summary>"""


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
            messages=[{"role": "user", "content": f"Analyze this document:\n\n{text}"}],
        )

        return self._parse_response(response.content[0].text)

    def _parse_response(self, text: str) -> DocumentInfo:
        lines = text.strip().split("\n")
        data = {}

        for line in lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                data[key.upper()] = value.strip()

        # Parse date
        doc_date = None
        date_str = data.get("DATE", "")
        if date_str and date_str.lower() != "unknown":
            try:
                doc_date = date.fromisoformat(date_str)
            except ValueError:
                logger.warning(f"Invalid date format: {date_str}")

        return DocumentInfo(
            title=data.get("TITLE", "Untitled"),
            subject=data.get("SUBJECT", ""),
            author=data.get("AUTHOR", "Unknown"),
            summary=data.get("SUMMARY", ""),
            date=doc_date,
        )
