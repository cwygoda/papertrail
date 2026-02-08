# Development commands for papertrail

# List available commands
default:
    @just --list

# Install dependencies and pre-commit hooks
bootstrap:
    uv sync --group dev
    uv run pre-commit install

# Run all checks (lint, typecheck, test)
check: lint typecheck test

# Run linter
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Fix lint issues
lint-fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run type checker
typecheck:
    uv run ty check src/

# Run tests
test *ARGS:
    uv run pytest {{ARGS}}

# Run tests with verbose output
test-v:
    uv run pytest -v

# Run a single test file or pattern
test-one PATTERN:
    uv run pytest -v -k "{{PATTERN}}"

# Process a single PDF (for testing)
process FILE:
    uv run papertrail process "{{FILE}}"

# Process without moving to storage
process-keep FILE:
    uv run papertrail process --keep "{{FILE}}"

# Run the file watcher
watch:
    uv run papertrail watch

# Clean up old trash files
cleanup:
    uv run papertrail cleanup

# Run pre-commit on all files
pre-commit:
    uv run pre-commit run --all-files
