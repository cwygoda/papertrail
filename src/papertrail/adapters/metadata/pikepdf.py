"""Metadata adapter using pikepdf and XMP sidecars."""

import logging
import sys
from pathlib import Path

import pikepdf

from ...domain.models import DocumentInfo
from ...ports.metadata import MetadataPort
from .xmp import write_xmp_sidecar

logger = logging.getLogger(__name__)

STEUERRELEVANT_TAG = "Steuerrelevant"


class PikePdfAdapter(MetadataPort):
    """Metadata implementation using pikepdf for PDF and XMP for sidecar."""

    def update_pdf(self, path: Path, info: DocumentInfo) -> None:
        logger.info(f"Updating PDF metadata: {path.name}")

        with pikepdf.open(path, allow_overwriting_input=True) as pdf:
            with pdf.open_metadata() as meta:
                meta["dc:title"] = info.title
                meta["dc:subject"] = info.subject
                meta["dc:creator"] = [info.issuer]
                meta["dc:description"] = info.summary
                if info.date:
                    meta["dc:date"] = info.date.isoformat()
                if info.steuerrelevant:
                    meta["xmp:Label"] = STEUERRELEVANT_TAG

            pdf.save(path)

        # Set macOS Finder tag for Spotlight search
        if sys.platform == "darwin" and info.steuerrelevant:
            self._set_finder_tag(path, STEUERRELEVANT_TAG)

        logger.info("PDF metadata updated")

    def _set_finder_tag(self, path: Path, tag: str) -> None:
        """Set macOS Finder tag for Spotlight search (tag:TagName)."""
        try:
            from osxmetadata import OSXMetaData

            md = OSXMetaData(str(path))
            tags = md.tags
            if isinstance(tags, list) and tag not in tags:
                md.tags = [*tags, tag]
                logger.debug(f"Added Finder tag: {tag}")
        except Exception as e:
            logger.warning(f"Failed to set Finder tag: {e}")

    def write_sidecar(self, path: Path, info: DocumentInfo) -> Path:
        logger.info(f"Writing XMP sidecar for: {path.name}")
        return write_xmp_sidecar(path, info)
