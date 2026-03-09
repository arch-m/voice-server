"""Pydantic settings primitives shared by all apps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.platform_common.env import DEFAULT_ENV_FILE, project_path, resolve_repo_path


class RepoSettings(BaseSettings):
    """Base settings class that always reads the repo root .env file."""

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RuntimePathsSettings(RepoSettings):
    """Common path settings shared by every runtime app."""

    models_dir: Path = Field(
        default_factory=lambda: project_path("models"),
        validation_alias="MODELS_DIR",
    )
    media_dir: Path = Field(
        default_factory=lambda: project_path("media"),
        validation_alias="MEDIA_DIR",
    )

    @field_validator("models_dir", "media_dir", mode="before")
    @classmethod
    def _resolve_repo_paths(cls, value: Any) -> Any:
        return resolve_repo_path(value)

    def models_path(self, *parts: str) -> Path:
        return self.models_dir.joinpath(*parts)

    def media_path(self, *parts: str) -> Path:
        return self.media_dir.joinpath(*parts)
