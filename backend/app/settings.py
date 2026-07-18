"""Explicit runtime configuration for the local-first demo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _split(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Onboard Repo Copilot API"
    app_version: str = "1.0.0"
    cors_origins: list[str] | None = None
    database_url: str = "sqlite:///./data/onboard_repo_copilot.db"
    allowed_repo_hosts: list[str] | None = None
    max_repo_files: int = 250
    max_repo_file_bytes: int = 250_000
    github_token: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            cors_origins=_split(os.getenv("CORS_ORIGINS", "http://localhost:5173")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/onboard_repo_copilot.db"),
            allowed_repo_hosts=_split(os.getenv("ALLOWED_REPO_HOSTS", "github.com,www.github.com")),
            max_repo_files=int(os.getenv("MAX_REPO_FILES", "250")),
            max_repo_file_bytes=int(os.getenv("MAX_REPO_FILE_BYTES", "250000")),
            github_token=os.getenv("GITHUB_TOKEN", "").strip(),
        )

    @property
    def database_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            raise ValueError("Only SQLite DATABASE_URL values are supported in this local release.")
        raw = self.database_url.removeprefix(prefix)
        return (ROOT_DIR / raw).resolve() if not raw.startswith("/") else Path(raw)


settings = Settings.from_env()
