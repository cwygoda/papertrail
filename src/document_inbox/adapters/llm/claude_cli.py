"""LLM adapter using Claude CLI."""

import json
import logging
import subprocess
from datetime import date

from ...domain.models import DocumentInfo
from ...ports.llm import LLMPort

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze this text of a scanned document - most likely in German - and extract:
- title: document title or descriptive name
- subject: main topic/category
- author: who wrote/sent/issued the document (or "Unknown")
- summary: 2-3 sentence summary
- date: document/issue date in YYYY-MM-DD format (or null if not found)

Document text:

{text}"""

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subject": {"type": "string"},
        "author": {"type": "string"},
        "summary": {"type": "string"},
        "date": {"type": ["string", "null"]},
    },
    "required": ["title", "subject", "author", "summary", "date"],
}


class ClaudeCLIAdapter(LLMPort):
    """LLM implementation using Claude CLI (uses subscription)."""

    def analyze(self, text: str) -> DocumentInfo:
        logger.info("Analyzing document with Claude CLI")

        # Truncate if too long
        if len(text) > 100_000:
            text = text[:100_000] + "\n\n[Truncated...]"

        prompt = ANALYSIS_PROMPT.format(text=text)

        result = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format", "json",
                "--json-schema", json.dumps(JSON_SCHEMA),
                prompt,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)
        content = data.get("structured_output", {})

        # Parse date
        doc_date = None
        if content.get("date"):
            try:
                doc_date = date.fromisoformat(content["date"])
            except ValueError:
                logger.warning(f"Invalid date format: {content['date']}")

        return DocumentInfo(
            title=content.get("title", "Untitled"),
            subject=content.get("subject", ""),
            author=content.get("author", "Unknown"),
            summary=content.get("summary", ""),
            date=doc_date,
        )
