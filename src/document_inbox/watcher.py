"""Filesystem watcher for iCloud Preview folder."""

import fnmatch
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .adapters.llm import ClaudeCLIAdapter
from .adapters.metadata import PikePdfAdapter
from .adapters.ocr import OcrMyPdfAdapter
from .adapters.platform import is_file_ready
from .adapters.storage import FilesystemAdapter
from .config import Settings
from .domain.services import ProcessingService

logger = logging.getLogger(__name__)

STABILITY_WAIT = 1.0  # seconds between checks
STABILITY_TIMEOUT = 30  # max seconds to wait


def create_processing_service(settings: Settings) -> ProcessingService:
    """Create a ProcessingService with configured adapters."""
    return ProcessingService(
        ocr=OcrMyPdfAdapter(),
        llm=ClaudeCLIAdapter(),
        metadata=PikePdfAdapter(),
        storage=FilesystemAdapter(settings.paths.base),
        quarantine_dir=settings.paths.quarantine,
    )


class DocumentHandler(FileSystemEventHandler):
    """Handle new document events from watchdog."""

    def __init__(self, settings: Settings, service: ProcessingService) -> None:
        self.settings = settings
        self.service = service
        self.patterns = settings.watch.patterns

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        path = Path(event.src_path)
        if self._matches_patterns(path):
            self._handle_file(path)

    def _matches_patterns(self, path: Path) -> bool:
        return any(fnmatch.fnmatch(path.name, p) for p in self.patterns)

    def _handle_file(self, path: Path) -> None:
        """Wait for stability, ingest, then process."""
        logger.info(f"New file detected: {path.name}")

        if not self._wait_for_stability(path):
            logger.warning(f"File never stabilized: {path.name}")
            return

        try:
            pending_path = self._ingest(path)
            self._process(pending_path)
        except Exception as e:
            logger.exception(f"Failed to handle {path.name}: {e}")

    def _wait_for_stability(self, path: Path) -> bool:
        """Wait until file is fully synced and ready.

        Uses NSURL resource keys on macOS to check iCloud sync status.
        """
        start = time.time()

        while time.time() - start < STABILITY_TIMEOUT:
            if not path.exists():
                return False

            if is_file_ready(path):
                return True

            time.sleep(STABILITY_WAIT)

        logger.warning(f"Timeout waiting for file: {path.name}")
        return path.exists() and path.stat().st_size > 0

    def _ingest(self, path: Path) -> Path:
        """Copy file to .pending, move original to .trash."""
        pending = self.settings.paths.pending
        trash = self.settings.paths.trash

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Copy to .pending
        dest = pending / path.name
        if dest.exists():
            dest = pending / f"{timestamp}_{path.name}"

        shutil.copy2(path, dest)
        logger.info(f"Copied to pending: {dest.name}")

        # Move original to .trash
        trash_name = f"{timestamp}_{path.name}"
        trash_path = trash / trash_name
        shutil.move(str(path), trash_path)
        logger.info(f"Moved to trash: {trash_name}")

        return dest

    def _process(self, path: Path) -> None:
        """Process file through the pipeline."""
        result = self.service.process(path)

        if result.success:
            logger.info(
                f"Processed: {path.name} -> {result.output_path.name}"
            )
        else:
            logger.error(f"Processing failed: {path.name} - {result.errors}")


def initial_scan(settings: Settings, service: ProcessingService) -> None:
    """Process any existing files on startup."""
    handler = DocumentHandler(settings, service)
    source = settings.paths.source

    if not source.exists():
        logger.warning(f"Source directory not found: {source}")
        return

    for pattern in settings.watch.patterns:
        for path in source.glob(pattern):
            if path.is_file():
                handler._handle_file(path)

    # Also process any files already in .pending
    for pattern in settings.watch.patterns:
        for path in settings.paths.pending.glob(pattern):
            if path.is_file():
                logger.info(f"Processing pending file: {path.name}")
                handler._process(path)


def run_watcher(settings: Settings) -> None:
    """Run the filesystem watcher daemon."""
    source = settings.paths.source

    if not source.exists():
        logger.error(f"Source directory not found: {source}")
        raise SystemExit(1)

    service = create_processing_service(settings)

    logger.info(f"Watching: {source}")
    logger.info(f"Pending: {settings.paths.pending}")
    logger.info(f"Trash: {settings.paths.trash}")
    logger.info(f"Quarantine: {settings.paths.quarantine}")
    logger.info(f"Output: {settings.paths.base}/yyyy/mm/")
    logger.info(f"Patterns: {settings.watch.patterns}")

    # Initial scan
    initial_scan(settings, service)

    # Start watcher
    handler = DocumentHandler(settings, service)
    observer = Observer()
    observer.schedule(handler, str(source), recursive=False)
    observer.start()

    try:
        while observer.is_alive():
            observer.join(timeout=1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        observer.stop()

    observer.join()
