"""Metadata adapter using pikepdf and YAML."""

import logging
from datetime import datetime
from pathlib import Path

import pikepdf
import yaml

from ...domain.models import DocumentInfo
from ...ports.metadata import MetadataPort

logger = logging.getLogger(__name__)


class PikePdfAdapter(MetadataPort):
    """Metadata implementation using pikepdf for PDF and YAML for sidecar."""

    def update_pdf(self, path: Path, info: DocumentInfo) -> None:
        logger.info(f"Updating PDF metadata: {path.name}")

        with pikepdf.open(path, allow_overwriting_input=True) as pdf:
            with pdf.open_metadata() as meta:
                meta["dc:title"] = info.title
                meta["dc:subject"] = info.subject
                meta["dc:creator"] = [info.author]
                meta["dc:description"] = info.summary
                if info.date:
                    meta["dc:date"] = info.date.isoformat()

            pdf.save(path)

        logger.info("PDF metadata updated")

    def write_sidecar(self, path: Path, info: DocumentInfo) -> Path:
        sidecar_path = path.with_suffix(".yaml")

        data = {
            "title": info.title,
            "subject": info.subject,
            "author": info.author,
            "date": info.date.isoformat() if info.date else None,
            "summary": info.summary,
            "processed_at": datetime.now().isoformat(),
            "source_file": path.name,
        }

        logger.info(f"Writing sidecar: {sidecar_path.name}")
        sidecar_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True)
        )

        return sidecar_path
