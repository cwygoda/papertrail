"""Platform-specific adapters."""

import sys

if sys.platform == "darwin":
    from .macos import is_file_ready
else:
    # Fallback for non-macOS
    from pathlib import Path

    def is_file_ready(path: Path) -> bool:
        """Fallback: assume file is ready if it exists and has size."""
        return path.exists() and path.stat().st_size > 0


__all__ = ["is_file_ready"]
