"""Configuration management using pydantic-settings."""

from pathlib import Path
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import tomllib
except ImportError:
    import tomli as tomllib

DEFAULT_SOURCE = "~/Library/Mobile Documents/com~apple~Preview/Documents"
DEFAULT_BASE = "~/Documents/Inbox"
DEFAULT_PATTERNS = ["*.pdf", "*.png", "*.jpg", "*.jpeg"]
DEFAULT_RETENTION_DAYS = 30
CONFIG_PATH = Path("~/.config/document-inbox/config.toml").expanduser()


class PathsConfig(BaseSettings):
    source: Path = Path(DEFAULT_SOURCE)
    base: Path = Path(DEFAULT_BASE)

    @field_validator("source", "base", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser()

    @property
    def pending(self) -> Path:
        return self.base / ".pending"

    @property
    def trash(self) -> Path:
        return self.base / ".trash"

    @property
    def quarantine(self) -> Path:
        return self.base / ".quarantine"


class CleanupConfig(BaseSettings):
    retention_days: int = DEFAULT_RETENTION_DAYS


class WatchConfig(BaseSettings):
    patterns: list[str] = DEFAULT_PATTERNS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCUMENT_INBOX_")

    paths: PathsConfig = PathsConfig()
    cleanup: CleanupConfig = CleanupConfig()
    watch: WatchConfig = WatchConfig()

    @model_validator(mode="after")
    def ensure_dirs(self) -> Self:
        self.paths.base.mkdir(parents=True, exist_ok=True)
        self.paths.pending.mkdir(parents=True, exist_ok=True)
        self.paths.trash.mkdir(parents=True, exist_ok=True)
        self.paths.quarantine.mkdir(parents=True, exist_ok=True)
        return self


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from TOML file, falling back to defaults."""
    path = config_path or CONFIG_PATH

    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)

        paths = PathsConfig(**data.get("paths", {}))
        cleanup = CleanupConfig(**data.get("cleanup", {}))
        watch = WatchConfig(**data.get("watch", {}))
        return Settings(paths=paths, cleanup=cleanup, watch=watch)

    return Settings()
