"""Storage adapter using local filesystem."""

import logging
import os
import re
import shutil
import stat
from datetime import date
from pathlib import Path

from ...domain.models import DocumentInfo
from ...ports.storage import StoragePort

logger = logging.getLogger(__name__)


def _clear_hidden_flag(path: Path) -> None:
    """Clear macOS hidden flag (UF_HIDDEN) if set."""
    try:
        current = os.stat(path).st_flags
        if current & stat.UF_HIDDEN:
            os.chflags(path, current & ~stat.UF_HIDDEN)
            logger.debug(f"Cleared hidden flag: {path.name}")
    except (OSError, AttributeError):
        # Not macOS or permission issue - ignore
        pass


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """Remove/replace characters invalid in filenames."""
    # Remove null bytes
    name = name.replace("\x00", "")
    # Replace path traversal attempts
    name = name.replace("..", "_")
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Collapse multiple spaces/underscores
    name = re.sub(r"[_\s]+", " ", name)
    # Remove leading/trailing dots and spaces
    name = name.strip(". ")
    # Limit length (leave room for date suffix + extension)
    if len(name) > max_length:
        name = name[:max_length].rsplit(" ", 1)[0]
    return name or "Untitled"


class FilesystemAdapter(StoragePort):
    """Storage implementation using local filesystem."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def store(self, path: Path, info: DocumentInfo) -> Path:
        """Store file in yyyy/mm/ structure with title-date naming."""
        doc_date = info.date or date.today()

        # Build destination directory: base/yyyy/mm/
        dest_dir = self.base_path / str(doc_date.year) / f"{doc_date.month:02d}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Build filename: "title - yyyy-mm-dd.ext"
        title = sanitize_filename(info.title)
        date_str = doc_date.isoformat()
        filename = f"{title} - {date_str}{path.suffix}"

        dest = dest_dir / filename

        # Handle collision
        if dest.exists():
            counter = 1
            while dest.exists():
                filename = f"{title} - {date_str} ({counter}){path.suffix}"
                dest = dest_dir / filename
                counter += 1

        shutil.move(str(path), dest)
        _clear_hidden_flag(dest)
        logger.info(f"Stored: {dest.relative_to(self.base_path)}")

        return dest

    def store_sidecar(self, pdf_path: Path, sidecar_path: Path) -> Path:
        """Store sidecar file alongside its PDF."""
        dest = pdf_path.with_suffix(sidecar_path.suffix)
        shutil.move(str(sidecar_path), dest)
        _clear_hidden_flag(dest)
        return dest

    def quarantine(self, path: Path, quarantine_dir: Path) -> Path:
        """Move file to quarantine."""
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        dest = quarantine_dir / path.name

        if dest.exists():
            counter = 1
            stem = path.stem
            while dest.exists():
                dest = quarantine_dir / f"{stem} ({counter}){path.suffix}"
                counter += 1

        shutil.move(str(path), dest)
        _clear_hidden_flag(dest)
        logger.warning(f"Quarantined: {path.name}")

        return dest
