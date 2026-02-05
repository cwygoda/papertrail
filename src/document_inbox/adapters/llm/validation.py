"""LLM response validation for prompt injection mitigation."""

import re

# Unique delimiters for document text boundaries
DOC_BEGIN = "<<<DOCUMENT_TEXT_BEGIN>>>"
DOC_END = "<<<DOCUMENT_TEXT_END>>>"

# Pattern for suspicious content: path traversal, code-like, control chars
_SUSPICIOUS_PATTERN = re.compile(r'\.\./|[{}<>`]|[\x00-\x1f]')


def looks_suspicious(text: str) -> bool:
    """Check if text looks like injection attempt."""
    if not text:
        return False
    return bool(_SUSPICIOUS_PATTERN.search(text))


def sanitize_field(text: str | None, fallback: str) -> str:
    """Return text if safe, otherwise fallback."""
    if not text:
        return fallback
    if looks_suspicious(text):
        return fallback
    return text
