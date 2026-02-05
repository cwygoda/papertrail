# Document Inbox

Watches the iCloud Preview folder for scanned documents, runs OCR, extracts metadata via LLM, and organizes them into a date-based folder structure.

## How it works

1. **Watch** - Monitors `~/Library/Mobile Documents/com~apple~Preview/Documents` for new files
2. **Ingest** - Copies to `.pending/`, moves original to `.trash/`
3. **OCR** - Runs ocrmypdf to extract/embed text
4. **Analyze** - LLM extracts title, subject, issuer, date, summary (German output)
5. **Store** - Moves to `yyyy/mm/` with embedded PDF metadata + YAML sidecar

Failed documents go to `.quarantine/` for manual review.

## Requirements

- macOS (uses iCloud + pyobjc for file stability checks)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) with `gemma3:4b` (default) or other model
- ocrmypdf + tesseract: `brew install ocrmypdf tesseract tesseract-lang`

## Installation

```bash
# Clone and install
git clone <repo-url>
cd document-inbox
uv sync

# Pull the default model
ollama pull gemma3:4b

# Copy config (optional - defaults work for most setups)
mkdir -p ~/.config/document-inbox
cp resources/config.example.toml ~/.config/document-inbox/config.toml

# Install launchd service (runs at login, auto-restarts)
uv run document-inbox install
```

## Usage

### CLI Commands

```bash
# Process a single file (for testing)
document-inbox process /path/to/document.pdf

# Process without moving to storage
document-inbox process --keep /path/to/document.pdf

# Run watcher manually
document-inbox watch

# Clean up old trash files
document-inbox cleanup

# Service management
document-inbox install    # Install launchd service
document-inbox uninstall  # Remove launchd service
```

### Logs

```bash
tail -f ~/Library/Logs/document-inbox.log
```

## Configuration

`~/.config/document-inbox/config.toml`:

```toml
[paths]
source = "~/Library/Mobile Documents/com~apple~Preview/Documents"
base = "~/Documents/Inbox"

[cleanup]
retention_days = 30

[watch]
patterns = ["*.pdf", "*.png", "*.jpg", "*.jpeg"]

[llm]
provider = "ollama"           # ollama | claude-cli | claude-api
model = "gemma3:4b"           # model name for ollama/claude-api
ollama_url = "http://localhost:11434"
```

### LLM Providers

| Provider | Description | Config |
|----------|-------------|--------|
| `ollama` | Local inference (default) | Requires Ollama running |
| `claude-cli` | Claude Code subscription | Uses `claude` CLI |
| `claude-api` | Anthropic API | Requires `ANTHROPIC_API_KEY` |

## Output Structure

```
~/Documents/Inbox/
├── .pending/      # Files being processed
├── .trash/        # Originals (purged after retention_days)
├── .quarantine/   # Failed processing
└── 2025/
    └── 02/
        ├── 2025-02-06_Stromrechnung_Stadtwerke.pdf
        └── 2025-02-06_Stromrechnung_Stadtwerke.yaml
```

### Sidecar YAML

```yaml
title: Stromrechnung Februar 2025
subject: Energieversorgung
issuer: Stadtwerke München
date: 2025-02-06
summary: Monatliche Stromabrechnung für den Abrechnungszeitraum Januar 2025...
processed_at: 2025-02-06T14:30:00
source_file: scan_001.pdf
```

## Architecture

Hexagonal architecture with ports/adapters:

- **Ports**: `LLMPort`, `OCRPort`, `MetadataPort`, `StoragePort`
- **Adapters**: Ollama, Claude CLI/API, ocrmypdf, pikepdf, filesystem
- **Domain**: `ProcessingService` orchestrates the pipeline

## License

MIT
