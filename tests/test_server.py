"""Integration tests for MCP server tools."""

import json
import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    """Use a temporary DB for every test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("ARCANA_DB_PATH", str(db_path))
    import arcana_mcp.db as db_mod
    db_mod._db = None
    db_mod.DB_PATH = db_path
    yield db_path
    if db_mod._db:
        db_mod._db.close()
        db_mod._db = None


def test_add_resource_and_read(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_read

    # Create a test file
    test_file = tmp_path / "hello.md"
    test_file.write_text("# Hello\nThis is test content.")

    result = json.loads(arcana_add_resource(str(test_file), to="arcana://test/hello"))
    assert result["added"] == 1

    content = arcana_read("arcana://test/hello")
    assert "Hello" in content
    assert "test content" in content


def test_add_and_rm(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_read, arcana_rm

    test_file = tmp_path / "removeme.md"
    test_file.write_text("# Remove\nThis will be removed.")

    arcana_add_resource(str(test_file), to="arcana://test/removeme")
    arcana_rm("arcana://test/removeme")

    result = json.loads(arcana_read("arcana://test/removeme"))
    assert "error" in result


def test_add_memory_and_search(tmp_db):
    from arcana_mcp.server import arcana_add_memory, arcana_find

    result = json.loads(arcana_add_memory(role="assistant", content="The database uses WAL mode for concurrent reads"))
    assert result["chunks"] >= 1
    assert result["uri"].startswith("arcana://memories/")

    # Semantic search should find it
    results = json.loads(arcana_find("WAL mode database"))
    assert len(results) >= 1
    assert "WAL" in results[0]["snippet"]


def test_ls_and_tree(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_ls, arcana_tree

    f1 = tmp_path / "a.md"
    f1.write_text("File A content")
    f2 = tmp_path / "b.md"
    f2.write_text("File B content")

    arcana_add_resource(str(f1), to="arcana://project/a")
    arcana_add_resource(str(f2), to="arcana://project/b")

    # ls at project level should show children
    ls_result = json.loads(arcana_ls("arcana://project"))
    assert "a" in ls_result
    assert "b" in ls_result

    tree_result = json.loads(arcana_tree("arcana://project"))
    assert len(tree_result) >= 2


def test_mkdir_and_mv(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_mkdir, arcana_mv, arcana_read

    arcana_mkdir("arcana://dest")

    f = tmp_path / "moveme.md"
    f.write_text("Move this content")
    arcana_add_resource(str(f), to="arcana://src/moveme")

    arcana_mv("arcana://src/moveme", "arcana://dest/moved")

    content = arcana_read("arcana://dest/moved")
    assert "Move this content" in content

    # Old URI should be gone
    result = json.loads(arcana_read("arcana://src/moveme"))
    assert "error" in result


def test_grep(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_grep

    f = tmp_path / "searchable.md"
    f.write_text("# Config\nThe server uses port 8080 for HTTP traffic.")

    arcana_add_resource(str(f), to="arcana://test/searchable")

    results = json.loads(arcana_grep(uri="arcana://test", pattern="port 8080"))
    assert len(results) >= 1


def test_stat(tmp_path, tmp_db):
    from arcana_mcp.server import arcana_add_resource, arcana_stat

    f = tmp_path / "stat.md"
    f.write_text("# Stats\nSome content for stats test.")

    arcana_add_resource(str(f), to="arcana://test/stat")

    result = json.loads(arcana_stat("arcana://test/stat"))
    assert result["uri"] == "arcana://test/stat"
    assert result["chunks"] >= 1
    assert result["total_chars"] > 0
