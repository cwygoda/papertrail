"""macOS-specific file status checks using NSURL resource keys."""

import logging
from pathlib import Path

from Foundation import (
    NSURL,
    NSURLUbiquitousItemDownloadingStatusCurrent,
    NSURLUbiquitousItemDownloadingStatusDownloaded,
    NSURLUbiquitousItemDownloadingStatusKey,
    NSURLUbiquitousItemIsDownloadingKey,
    NSURLUbiquitousItemIsUploadingKey,
)

logger = logging.getLogger(__name__)


def is_file_ready(path: Path) -> bool:
    """Check if file is fully synced and ready for processing.

    Uses NSURL resource keys to check iCloud sync status:
    - Not uploading
    - Not downloading
    - Download status is Current or Downloaded

    For non-iCloud files, returns True if file exists with size > 0.
    """
    if not path.exists():
        return False

    if path.stat().st_size == 0:
        return False

    url = NSURL.fileURLWithPath_(str(path))

    # Check if file is being uploaded
    is_uploading = _get_resource_value(url, NSURLUbiquitousItemIsUploadingKey)
    if is_uploading:
        logger.debug(f"File is uploading: {path.name}")
        return False

    # Check if file is being downloaded
    is_downloading = _get_resource_value(url, NSURLUbiquitousItemIsDownloadingKey)
    if is_downloading:
        logger.debug(f"File is downloading: {path.name}")
        return False

    # Check download status
    status = _get_resource_value(url, NSURLUbiquitousItemDownloadingStatusKey)

    # For non-iCloud files, status will be None - that's OK
    if status is None:
        return True

    # For iCloud files, check if fully synced
    ready = status in (
        NSURLUbiquitousItemDownloadingStatusCurrent,
        NSURLUbiquitousItemDownloadingStatusDownloaded,
    )

    if not ready:
        logger.debug(f"File not ready (status={status}): {path.name}")

    return ready


def _get_resource_value(url: NSURL, key: str):
    """Get a resource value from NSURL, returning None on error."""
    success, value, error = url.getResourceValue_forKey_error_(None, key, None)
    if not success or error:
        return None
    return value
