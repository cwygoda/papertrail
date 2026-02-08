# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
uv sync                     # Install dependencies
uv sync --group dev         # Install with dev dependencies
uv run pytest               # Run all tests
uv run pytest -v            # Verbose test output
uv run pytest tests/unit/   # Run only unit tests
uv run pytest -k "test_name"  # Run specific test by name
uv run papertrail process /path/to.pdf  # Test single file processing
```

## Architecture

Hexagonal (ports/adapters) architecture for document processing:

```
src/papertrail/
├── domain/
│   ├── models.py       # DocumentInfo, ProcessingResult dataclasses
│   └── services.py     # ProcessingService - 6-step pipeline orchestration
├── ports/              # Abstract interfaces
│   ├── llm.py          # LLMPort.analyze(text) -> DocumentInfo
│   ├── ocr.py          # OCRPort.process(), extract_text()
│   ├── metadata.py     # MetadataPort.update_pdf(), write_sidecar()
│   └── storage.py      # StoragePort.store(), quarantine()
├── adapters/           # Concrete implementations
│   ├── llm/            # Ollama (default), Claude CLI, Claude API
│   ├── ocr/            # ocrmypdf wrapper
│   ├── metadata/       # pikepdf for PDF metadata
│   ├── storage/        # Filesystem with date-based organization
│   └── platform/       # macOS iCloud file stability checks
├── config.py           # pydantic-settings, TOML config loading
├── watcher.py          # watchdog-based file monitor
└── __main__.py         # Click CLI entry point
```

### Processing Pipeline (ProcessingService.process)

1. OCR via ocrmypdf
2. Extract text
3. LLM analysis → DocumentInfo (title, subject, issuer, date, summary)
4. Embed metadata in PDF (pikepdf)
5. Write YAML sidecar
6. Move to `yyyy/mm/` storage structure

Failed files → quarantine directory.

### LLM Adapter Factory

`adapters/llm/__init__.py:create_llm_adapter()` selects provider based on config:
- `ollama` - Local inference (default)
- `claude-cli` - Uses Claude Code CLI
- `claude-api` - Anthropic API (requires ANTHROPIC_API_KEY)

### Security

`adapters/llm/validation.py` - Prompt injection mitigation with `looks_suspicious()` and `sanitize_field()` for LLM responses.

## Testing

- **Unit tests**: `tests/unit/` - models, validation, filesystem sanitization
- **BDD tests**: `tests/bdd/` - feature files in `features/`, step definitions in `test_*.py`

Tests use mock ports to isolate domain logic from adapters.
