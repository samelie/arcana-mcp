"""Tests for SQLite database connection and schema."""

import os
import sqlite3
import tempfile

import pytest


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    """Use a temporary DB for every test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("ARCANA_DB_PATH", str(db_path))
    # Reset singleton
    import arcana_mcp.db as db_mod
    db_mod._db = None
    db_mod.DB_PATH = db_path
    yield db_path
    if db_mod._db:
        db_mod._db.close()
        db_mod._db = None


def test_schema_creation(tmp_db):
    from arcana_mcp.db import _get_db

    db = _get_db()
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "resources" in tables
    assert "chunks" in tables
    assert "directories" in tables
    assert "meta" in tables
    assert "chunks_fts" in tables


def test_crud_resource(tmp_db):
    from arcana_mcp.db import _get_db

    db = _get_db()
    db.execute(
        "INSERT INTO resources (uri, source_path, kind) VALUES (?, ?, ?)",
        ("arcana://test", "/tmp/test.md", "file"),
    )
    db.commit()

    row = db.execute("SELECT uri, kind FROM resources WHERE uri = ?", ("arcana://test",)).fetchone()
    assert row == ("arcana://test", "file")

    db.execute("DELETE FROM resources WHERE uri = ?", ("arcana://test",))
    db.commit()
    assert db.execute("SELECT COUNT(*) FROM resources WHERE uri = ?", ("arcana://test",)).fetchone()[0] == 0


def test_cascade_delete(tmp_db):
    from arcana_mcp.db import _get_db

    db = _get_db()
    db.execute("INSERT INTO resources (uri, source_path, kind) VALUES (?, ?, ?)", ("arcana://cascade", "/tmp/c.md", "file"))
    db.execute("INSERT INTO chunks (resource_uri, chunk_index, content) VALUES (?, ?, ?)", ("arcana://cascade", 0, "test content"))
    db.commit()

    assert db.execute("SELECT COUNT(*) FROM chunks WHERE resource_uri = ?", ("arcana://cascade",)).fetchone()[0] == 1

    db.execute("DELETE FROM resources WHERE uri = ?", ("arcana://cascade",))
    db.commit()

    assert db.execute("SELECT COUNT(*) FROM chunks WHERE resource_uri = ?", ("arcana://cascade",)).fetchone()[0] == 0


def test_fts_trigger(tmp_db):
    from arcana_mcp.db import _get_db

    db = _get_db()
    db.execute("INSERT INTO resources (uri, source_path, kind) VALUES (?, ?, ?)", ("arcana://fts-test", "/tmp/f.md", "file"))
    db.execute("INSERT INTO chunks (resource_uri, chunk_index, content) VALUES (?, ?, ?)", ("arcana://fts-test", 0, "kubernetes deployment rollout"))
    db.commit()

    results = db.execute("SELECT resource_uri FROM chunks_fts WHERE chunks_fts MATCH ?", ('"kubernetes"',)).fetchall()
    assert len(results) >= 1
    assert results[0][0] == "arcana://fts-test"
