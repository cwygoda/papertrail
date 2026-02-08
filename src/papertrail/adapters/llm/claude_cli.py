"""LLM adapter using Claude CLI."""

import json
import logging
import subprocess
from datetime import date

from ...domain.models import DocumentInfo
from ...ports.llm import LLMPort
from .prompts import SYSTEM_PROMPT
from .validation import DOC_BEGIN, DOC_END, looks_suspicious, sanitize_field

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = f"{SYSTEM_PROMPT}\n\n{DOC_BEGIN}\n{{text}}\n{DOC_END}"

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "subject": {"type": "string"},
        "issuer": {"type": "string"},
        "summary": {"type": "string"},
        "date": {"type": ["string", "null"]},
        "steuerrelevant": {"type": "boolean"},
    },
    "required": ["title", "subject", "issuer", "summary", "date", "steuerrelevant"],
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
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(JSON_SCHEMA),
            ],
            input=prompt,
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

        title = sanitize_field(content.get("title"), "Untitled")
        subject = sanitize_field(content.get("subject"), "")
        issuer = sanitize_field(content.get("issuer"), "Unknown")

        if looks_suspicious(content.get("title", "")):
            title_preview = content.get("title", "")[:50]
            logger.warning(f"Suspicious title rejected: {title_preview}")

        return DocumentInfo(
            title=title,
            subject=subject,
            issuer=issuer,
            summary=content.get("summary", ""),  # Allow free-form text
            date=doc_date,
            steuerrelevant=bool(content.get("steuerrelevant", False)),
        )
