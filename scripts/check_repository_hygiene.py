"""Fail CI when tracked repository files violate basic hygiene safeguards."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"
    ),
    "OpenAI-style key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
}


def tracked_files() -> list[Path]:
    """Return tracked files without inspecting ignored or local-only content."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def repository_files() -> list[Path]:
    """Return tracked and non-ignored untracked files for local scanning."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in result.stdout.split(b"\0") if item]


def main() -> None:
    """Validate required files, ignored artifacts, and obvious credential forms."""
    files = tracked_files()
    tracked = {path.as_posix() for path in files}
    failures: list[str] = []

    tracked_env = [
        path
        for path in tracked
        if Path(path).name.startswith(".env") and path != ".env.example"
    ]
    if tracked_env:
        failures.append("environment files are tracked: " + ", ".join(tracked_env))

    generated = [
        path.as_posix()
        for path in files
        if GENERATED_PARTS.intersection(path.parts) or path.suffix in {".pyc", ".pyo"}
    ]
    if generated:
        failures.append(
            "generated caches or build output are tracked: " + ", ".join(generated)
        )

    if "frontend/package-lock.json" not in tracked:
        failures.append("frontend/package-lock.json is not tracked")
    if not any(
        path.startswith("alembic/versions/") and path.endswith(".py")
        for path in tracked
    ):
        failures.append("no Alembic migration files are tracked")

    scan_exclusions = {".env.example", "frontend/package-lock.json"}
    for relative_path in repository_files():
        path_string = relative_path.as_posix()
        if path_string in scan_exclusions:
            continue
        path = ROOT / relative_path
        try:
            if path.stat().st_size > 1_000_000:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                failures.append(f"possible {label} found in {path_string}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        raise SystemExit(1)
    print("Repository hygiene checks passed.")


if __name__ == "__main__":
    main()
