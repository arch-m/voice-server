"""Filesystem helpers shared across apps and packages."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def project_path(*parts: str) -> Path:
    """Return an absolute path rooted at the repository root."""
    return PROJECT_ROOT.joinpath(*parts)


def resolve_repo_path(value: str | Path | None, default: str | Path | None = None) -> Path | None:
    """Resolve a path value against the repository root."""
    candidate = default if value in (None, "") else value
    if candidate is None:
        return None

    path = candidate if isinstance(candidate, Path) else Path(candidate).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()
