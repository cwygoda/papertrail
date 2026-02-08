"""Cleanup old trash files based on retention policy."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from .config import Settings

logger = logging.getLogger(__name__)


def run_cleanup(settings: Settings) -> int:
    """Remove trash files older than retention period.

    Returns number of files removed.
    """
    trash = settings.paths.trash
    retention_days = settings.cleanup.retention_days
    cutoff = datetime.now() - timedelta(days=retention_days)

    if not trash.exists():
        logger.warning(f"Trash directory not found: {trash}")
        return 0

    removed = 0
    for path in trash.iterdir():
        if not path.is_file():
            continue

        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if mtime < cutoff:
            logger.info(f"Removing old file: {path.name}")
            path.unlink()
            removed += 1

    logger.info(f"Cleanup complete: {removed} files removed from trash")
    return removed
