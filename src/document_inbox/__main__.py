"""CLI entry point for document-inbox."""

import logging
import subprocess
import sys
from pathlib import Path

import click

from .adapters.llm import ClaudeCLIAdapter
from .adapters.metadata import PikePdfAdapter
from .adapters.ocr import OcrMyPdfAdapter
from .adapters.storage import FilesystemAdapter
from .cleanup import run_cleanup
from .config import load_settings
from .domain.services import ProcessingService
from .watcher import run_watcher

PLIST_NAME = "com.cwygoda.document-inbox.plist"
LAUNCHAGENTS_DIR = Path("~/Library/LaunchAgents").expanduser()
LOGS_DIR = Path("~/Library/Logs").expanduser()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
@click.option(
    "-c", "--config", type=click.Path(exists=True), help="Config file path"
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config: str | None) -> None:
    """Document Inbox - iCloud Preview folder watcher."""
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
        llm=ClaudeCLIAdapter(),
        metadata=PikePdfAdapter(),
        storage=FilesystemAdapter(settings.paths.base),
        quarantine_dir=settings.paths.quarantine if not keep else None,
    )

    result = service.process(file, keep=keep)

    if result.success:
        click.echo(f"title: {result.document_info.title}")
        click.echo(f"subject: {result.document_info.subject}")
        click.echo(f"author: {result.document_info.author}")
        click.echo(f"date: {result.document_info.date}")
        click.echo(f"summary: {result.document_info.summary}")
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


@cli.command()
def install() -> None:
    """Install launchd service."""
    plist_src = Path(__file__).parent.parent.parent.parent / PLIST_NAME
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
