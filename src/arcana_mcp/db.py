"""SQLite database connection and schema management."""

import logging
import os
import sqlite3
from pathlib import Path

from .embeddings import EMBED_MODEL, _embed_texts, _pack_embedding

logger = logging.getLogger("arcana-mcp")

DB_PATH = Path(os.environ.get("ARCANA_DB_PATH", Path.home() / ".arcana" / "context.db"))

_db: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    global _db
    if _db is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _db = sqlite3.connect(str(DB_PATH))
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("PRAGMA foreign_keys=ON")
        _init_schema(_db)
        _migrate_embeddings(_db)
    return _db


def _init_schema(db: sqlite3.Connection):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS resources (
            uri TEXT PRIMARY KEY, source_path TEXT, kind TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_uri TEXT NOT NULL REFERENCES resources(uri) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL, content TEXT NOT NULL,
            embedding BLOB,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(resource_uri, chunk_index)
        );
        CREATE TABLE IF NOT EXISTS directories (
            uri TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # FTS5 — idempotent
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, resource_uri, content='chunks', content_rowid='id')")
    except sqlite3.OperationalError:
        pass  # already exists
    # Triggers for FTS sync
    for sql in [
        """CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, content, resource_uri) VALUES (new.id, new.content, new.resource_uri);
        END""",
        """CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, content, resource_uri) VALUES ('delete', old.id, old.content, old.resource_uri);
        END""",
        """CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, content, resource_uri) VALUES ('delete', old.id, old.content, old.resource_uri);
            INSERT INTO chunks_fts(rowid, content, resource_uri) VALUES (new.id, new.content, new.resource_uri);
        END""",
    ]:
        try:
            db.execute(sql)
        except sqlite3.OperationalError:
            pass
    db.commit()


def _migrate_embeddings(db: sqlite3.Connection):
    """Check embed model; NULL old embeddings and re-embed if model changed."""
    from .embeddings import EMBED_DIM

    row = db.execute("SELECT value FROM meta WHERE key='embed_model'").fetchone()
    stored_model = row[0] if row else None

    # Check if re-embedding needed: model name mismatch or dimension mismatch
    needs_reembed = stored_model != EMBED_MODEL
    if not needs_reembed:
        sample = db.execute("SELECT embedding FROM chunks WHERE embedding IS NOT NULL LIMIT 1").fetchone()
        if sample and len(sample[0]) != EMBED_DIM * 4:
            needs_reembed = True
            logger.warning(f"Embedding dimension mismatch: stored={len(sample[0])//4}, expected={EMBED_DIM}")

    if not needs_reembed:
        return

    logger.info(f"Embed model changed {stored_model} → {EMBED_MODEL}, clearing embeddings")
    db.execute("UPDATE chunks SET embedding = NULL")
    db.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('embed_model', ?)",
        (EMBED_MODEL,),
    )
    db.commit()

    # Eager re-embed all chunks with NULL embeddings
    rows = db.execute("SELECT id, content FROM chunks WHERE embedding IS NULL").fetchall()
    if not rows:
        return

    logger.info(f"Re-embedding {len(rows)} chunks with {EMBED_MODEL}")
    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]
    embeddings = _embed_texts(texts)

    for chunk_id, emb in zip(ids, embeddings):
        db.execute(
            "UPDATE chunks SET embedding = ? WHERE id = ?",
            (_pack_embedding(emb), chunk_id),
        )
    db.commit()
    logger.info(f"Re-embedded {len(rows)} chunks")
