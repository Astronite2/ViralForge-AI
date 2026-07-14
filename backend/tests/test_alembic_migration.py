"""Alembic migration validation tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sqlalchemy import create_engine, inspect

import backend.app.models  # noqa: F401
from backend.app.db.base import Base


def test_metadata_includes_all_expected_tables() -> None:
    """Ensure Alembic sees every intended SQLAlchemy model."""
    expected_tables = {
        "analyses",
        "channels",
        "content",
        "decision_explanations",
        "decisions",
        "evidence",
        "historical_evidence",
        "historical_observations",
        "metrics",
        "opportunities",
        "opportunity_scores",
        "platforms",
        "processed_events",
        "reasoning_results",
        "reasoning_runs",
        "reasoning_source_links",
        "reasoning_validation_errors",
        "topics",
        "topic_relationships",
        "trend_signals",
        "users",
        "videos",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_migration_foreign_keys_reference_existing_tables(
    tmp_path: Path,
) -> None:
    """Upgrade the migration and verify foreign-key targets exist."""
    db_url = _sqlite_url(tmp_path / "migration.db")
    _run_alembic("upgrade", "head", db_url=db_url)

    engine = create_engine(db_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        for table_name in tables:
            for foreign_key in inspector.get_foreign_keys(table_name):
                referred_table = foreign_key.get("referred_table")
                assert referred_table is not None
                assert referred_table in tables
    finally:
        engine.dispose()


def test_migration_upgrade_downgrade_reupgrade_and_current(
    tmp_path: Path,
) -> None:
    """Run the full alembic lifecycle against a disposable database."""
    db_url = _sqlite_url(tmp_path / "alembic.db")
    _run_alembic("upgrade", "head", db_url=db_url)
    _run_alembic("current", db_url=db_url, expect_revision=True)
    _run_alembic("downgrade", "base", db_url=db_url)
    _run_alembic("upgrade", "head", db_url=db_url)
    output = _run_alembic("current", db_url=db_url, expect_revision=True)
    assert "0005_project_workspace" in output


def _run_alembic(*args: str, db_url: str, expect_revision: bool = False) -> str:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    result = subprocess.run(  # noqa: S603,S607
        ["python3", "-m", "alembic", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    output = result.stdout + result.stderr
    if expect_revision:
        assert "0005_project_workspace" in output
    return output


def _sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path}"
