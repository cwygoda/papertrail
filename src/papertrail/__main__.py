"""CLI entry point for papertrail."""

import logging
import re
import subprocess
import sys
from pathlib import Path

import click
import yaml

from .adapters.llm import create_llm_adapter
from .adapters.metadata import PikePdfAdapter
from .adapters.ocr import OcrMyPdfAdapter
from .adapters.storage import FilesystemAdapter
from .cleanup import run_cleanup
from .config import load_settings
from .domain.services import ProcessingService, ReprocessingService
from .watcher import run_watcher

logger = logging.getLogger(__name__)

PLIST_NAME = "com.cwygoda.papertrail.plist"
LAUNCHAGENTS_DIR = Path("~/Library/LaunchAgents").expanduser()
LOGS_DIR = Path("~/Library/Logs").expanduser()
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.option("-c", "--config", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
    """Papertrail - iCloud Preview folder watcher."""
    setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = Path(config) if config else None


@cli.command()
@click.pass_context
def watch(ctx: click.Context) -> None:
    """Run the document watcher daemon."""
    settings = load_settings(ctx.obj["config_path"])
    run_watcher(settings)


@cli.command()
@click.pass_context
def cleanup(ctx: click.Context) -> None:
    """Remove old files from trash."""
    settings = load_settings(ctx.obj["config_path"])
    removed = run_cleanup(settings)
    click.echo(f"Removed {removed} files from trash")


@cli.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--keep", is_flag=True, help="Keep file in place (don't move to storage)")
@click.pass_context
def process(ctx: click.Context, file: Path, keep: bool) -> None:
    """Process a single document file."""
    settings = load_settings(ctx.obj["config_path"])

    # Wire up adapters
    service = ProcessingService(
        ocr=OcrMyPdfAdapter(),
        llm=create_llm_adapter(settings.llm),
        metadata=PikePdfAdapter(),
        storage=FilesystemAdapter(settings.paths.base),
        quarantine_dir=settings.paths.quarantine if not keep else None,
    )

    result = service.process(file, keep=keep)

    if result.success and result.document_info:
        click.echo(f"title: {result.document_info.title}")
        click.echo(f"subject: {result.document_info.subject}")
        click.echo(f"issuer: {result.document_info.issuer}")
        click.echo(f"date: {result.document_info.date}")
        click.echo(f"summary: {result.document_info.summary}")
        click.echo(f"steuerrelevant: {result.document_info.steuerrelevant}")
        click.echo(f"text_length: {result.text_length}")
        if result.output_path:
            click.echo(f"output: {result.output_path}")
        if result.sidecar_path:
            click.echo(f"sidecar: {result.sidecar_path}")
    else:
        click.echo(f"Errors: {result.errors}", err=True)
        if result.output_path:
            click.echo(f"Quarantined: {result.output_path}", err=True)
        sys.exit(1)


def collect_pdfs(path: Path, recursive: bool) -> list[Path]:
    """Collect PDF files from path (file or directory)."""
    if path.is_file():
        return [path] if path.suffix.lower() == ".pdf" else []
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path.glob(pattern))


def parse_date_range(date_range: str) -> tuple[str, str]:
    """Parse YYYY-MM-DD..YYYY-MM-DD into (start, end)."""
    if ".." not in date_range:
        raise click.BadParameter("Date range must be YYYY-MM-DD..YYYY-MM-DD")
    start, end = date_range.split("..", 1)
    if not DATE_PATTERN.match(start) or not DATE_PATTERN.match(end):
        raise click.BadParameter("Date range must be YYYY-MM-DD..YYYY-MM-DD")
    if start > end:
        raise click.BadParameter("Start date must be before end date")
    return start, end


def in_date_range(path: Path, start: str, end: str) -> bool:
    """Check if file path's yyyy/mm/ folder falls within date range.

    Uses month granularity: a file in 2024/03/ matches if 2024-03-01 is
    within [start, end]. Day component of the range bounds is respected.
    """
    parts = path.parts
    for i, part in enumerate(parts):
        if len(part) == 4 and part.isdigit() and i + 1 < len(parts):
            year = part
            month = parts[i + 1]
            if len(month) == 2 and month.isdigit():
                date_str = f"{year}-{month}-01"
                return start <= date_str <= end
    return False


def is_missing_field(path: Path, field: str) -> bool:
    """Check if sidecar YAML is missing a field."""
    sidecar = path.with_suffix(".yaml")
    if not sidecar.exists():
        return True
    try:
        data = yaml.safe_load(sidecar.read_text())
        return data is None or field not in data or data[field] is None
    except Exception as e:
        logger.warning(f"Failed to parse sidecar {sidecar}: {e}")
        return True


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--recursive/--no-recursive", default=True, help="Process recursively")
@click.option("--dry-run", is_flag=True, help="Show what would be processed")
@click.option("--filter-date", help="YYYY-MM-DD..YYYY-MM-DD (month granularity)")
@click.option("--missing-field", help="Only files missing this sidecar field")
@click.pass_context
def reprocess(
    ctx: click.Context,
    path: Path,
    recursive: bool,
    dry_run: bool,
    filter_date: str | None,
    missing_field: str | None,
) -> None:
    """Reprocess stored documents (update metadata in-place)."""
    settings = load_settings(ctx.obj["config_path"])

    # Collect PDFs
    pdfs = collect_pdfs(path, recursive)

    # Apply filters
    if filter_date:
        start, end = parse_date_range(filter_date)
        pdfs = [p for p in pdfs if in_date_range(p, start, end)]

    if missing_field:
        pdfs = [p for p in pdfs if is_missing_field(p, missing_field)]

    if not pdfs:
        click.echo("No files to reprocess")
        return

    if dry_run:
        click.echo(f"Would reprocess {len(pdfs)} files:")
        for p in pdfs:
            click.echo(f"  {p}")
        return

    # Wire up service
    service = ReprocessingService(
        ocr=OcrMyPdfAdapter(),
        llm=create_llm_adapter(settings.llm),
        metadata=PikePdfAdapter(),
    )

    success_count = 0
    error_count = 0

    for pdf in pdfs:
        result = service.reprocess(pdf)
        if result.success:
            success_count += 1
            if result.document_info:
                tax = result.document_info.steuerrelevant
                click.echo(f"✓ {pdf.name}: steuerrelevant={tax}")
        else:
            error_count += 1
            click.echo(f"✗ {pdf.name}: {result.errors}", err=True)

    click.echo(f"\nReprocessed: {success_count} success, {error_count} errors")


@cli.command()
def install() -> None:
    """Install launchd service."""
    plist_src = Path(__file__).parent.parent.parent / "resources" / PLIST_NAME
    plist_dest = LAUNCHAGENTS_DIR / PLIST_NAME

    if not plist_src.exists():
        click.echo(f"Error: plist not found at {plist_src}", err=True)
        sys.exit(1)

    LAUNCHAGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Copy plist
    plist_dest.write_text(plist_src.read_text())
    click.echo(f"Installed: {plist_dest}")

    # Load service
    subprocess.run(["launchctl", "load", str(plist_dest)], check=True)
    click.echo("Service loaded")


@cli.command()
def uninstall() -> None:
    """Remove launchd service."""
    plist_path = LAUNCHAGENTS_DIR / PLIST_NAME

    if not plist_path.exists():
        click.echo("Service not installed")
        return

    # Unload service
    subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
    click.echo("Service unloaded")

    # Remove plist
    plist_path.unlink()
    click.echo(f"Removed: {plist_path}")


if __name__ == "__main__":
    cli()
