"""FastMCP server with all 12 tool functions."""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .chunking import TEXT_EXTS, _auto_uri, _chunk_text
from .db import _get_db
from .embeddings import _cosine_sim, _embed_texts, _pack_embedding, _unpack_embedding

logger = logging.getLogger("context-db")

mcp_server = FastMCP(
    "context-db",
    instructions="Minimal context database — semantic search, FTS, resource management",
)


@mcp_server.tool()
def ov_add_resource(path: str, to: str = "", reason: str = "") -> str:
    """Add a file or directory as a resource into the context database.

    Args:
        path: Local file or directory path to index.
        to: Target arcana:// URI (optional, auto-determined if empty).
        reason: Why this resource is being added.
    """
    db = _get_db()
    p = Path(path).expanduser().resolve()
    if not p.exists():
        return json.dumps({"error": f"Path not found: {path}"})

    files: list[tuple[str, str]] = []  # (uri, filepath)
    if p.is_dir():
        base_uri = to.rstrip("/") if to else f"arcana://{p.name}"
        for root, _, filenames in os.walk(p):
            for fname in filenames:
                fp = Path(root) / fname
                if fp.suffix.lower() in TEXT_EXTS:
                    rel = fp.relative_to(p)
                    uri = f"{base_uri}/{rel}"
                    files.append((uri, str(fp)))
    else:
        uri = to if to else _auto_uri(str(p))
        files.append((uri, str(p)))

    added = 0
    for uri, filepath in files:
        try:
            text = Path(filepath).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Skip {filepath}: {e}")
            continue
        chunks = _chunk_text(text, filepath)
        if not chunks:
            continue
        embeddings = _embed_texts(chunks)

        # Upsert resource
        db.execute(
            "INSERT OR REPLACE INTO resources (uri, source_path, kind, metadata, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (uri, filepath, "file", json.dumps({"reason": reason}) if reason else "{}"),
        )
        # Clear old chunks
        db.execute("DELETE FROM chunks WHERE resource_uri = ?", (uri,))
        # Insert new chunks
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.execute(
                "INSERT INTO chunks (resource_uri, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                (uri, idx, chunk, _pack_embedding(emb)),
            )
        added += 1
    db.commit()
    return json.dumps({"added": added, "total_files": len(files)})


@mcp_server.tool()
def ov_ls(uri: str = "arcana://") -> str:
    """List direct children at a arcana:// URI.

    Args:
        uri: arcana:// URI to list (default: root).
    """
    db = _get_db()
    prefix = uri.rstrip("/") + "/"

    # Get resources and directories under this prefix (direct children only)
    items = set()
    for (u,) in db.execute("SELECT uri FROM resources WHERE uri LIKE ? || '%'", (prefix,)):
        rest = u[len(prefix):]
        child = rest.split("/")[0]
        if child:
            items.add(child)
    for (u,) in db.execute("SELECT uri FROM directories WHERE uri LIKE ? || '%'", (prefix,)):
        rest = u[len(prefix):]
        child = rest.split("/")[0]
        if child:
            items.add(child)
    return json.dumps(sorted(items))


@mcp_server.tool()
def ov_tree(uri: str = "arcana://") -> str:
    """Show recursive tree at a arcana:// URI.

    Args:
        uri: arcana:// URI to show tree for (default: root).
    """
    db = _get_db()
    prefix = uri.rstrip("/") + "/"
    rows = db.execute("SELECT uri FROM resources WHERE uri LIKE ? || '%' ORDER BY uri", (prefix,)).fetchall()
    dir_rows = db.execute("SELECT uri FROM directories WHERE uri LIKE ? || '%' ORDER BY uri", (prefix,)).fetchall()
    tree = [r[0] for r in dir_rows] + [r[0] for r in rows]
    return json.dumps(tree)


@mcp_server.tool()
def ov_stat(uri: str) -> str:
    """Get metadata for a resource.

    Args:
        uri: arcana:// URI to get metadata for.
    """
    db = _get_db()
    row = db.execute("SELECT uri, source_path, kind, created_at, updated_at, metadata FROM resources WHERE uri = ?", (uri,)).fetchone()
    if not row:
        return json.dumps({"error": f"Not found: {uri}"})
    chunk_count = db.execute("SELECT COUNT(*), SUM(LENGTH(content)) FROM chunks WHERE resource_uri = ?", (uri,)).fetchone()
    return json.dumps({
        "uri": row[0], "source_path": row[1], "kind": row[2],
        "created_at": row[3], "updated_at": row[4],
        "metadata": json.loads(row[5]) if row[5] else {},
        "chunks": chunk_count[0], "total_chars": chunk_count[1] or 0,
    })


@mcp_server.tool()
def ov_rm(uri: str, recursive: bool = False) -> str:
    """Remove a resource (CASCADE deletes chunks, FTS triggers clean up).

    Args:
        uri: arcana:// URI to remove.
        recursive: Remove all resources under this URI prefix.
    """
    db = _get_db()
    if recursive:
        prefix = uri.rstrip("/") + "/"
        db.execute("DELETE FROM resources WHERE uri = ? OR uri LIKE ? || '%'", (uri, prefix))
        db.execute("DELETE FROM directories WHERE uri = ? OR uri LIKE ? || '%'", (uri, prefix))
    else:
        db.execute("DELETE FROM resources WHERE uri = ?", (uri,))
        db.execute("DELETE FROM directories WHERE uri = ?", (uri,))
    db.commit()
    return f"Removed {uri}"


@mcp_server.tool()
def ov_find(query: str, target_uri: str = "", limit: int = 10) -> str:
    """Semantic search — embed query, cosine similarity against all chunks.

    Args:
        query: Natural language search query.
        target_uri: Scope search to a specific arcana:// URI prefix (optional).
        limit: Max number of results (default 10).
    """
    db = _get_db()
    q_emb = _embed_texts([query])[0]

    sql = "SELECT id, resource_uri, chunk_index, content, embedding FROM chunks"
    params: list[Any] = []
    if target_uri:
        prefix = target_uri.rstrip("/")
        sql += " WHERE resource_uri = ? OR resource_uri LIKE ? || '/%'"
        params = [prefix, prefix]

    rows = db.execute(sql, params).fetchall()
    scored = []
    for row in rows:
        if row[4] is None:
            continue
        emb = _unpack_embedding(row[4])
        sim = _cosine_sim(q_emb, emb)
        scored.append({"uri": row[1], "chunk_index": row[2], "score": round(sim, 4), "snippet": row[3][:300]})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps(scored[:limit])


@mcp_server.tool()
def ov_grep(uri: str = "arcana://", pattern: str = "", case_insensitive: bool = False) -> str:
    """Keyword/regex search — FTS5 for simple terms, Python re fallback.

    Args:
        uri: arcana:// URI to search within.
        pattern: Search pattern (keyword or regex).
        case_insensitive: Case-insensitive matching.
    """
    db = _get_db()
    results = []

    # Try FTS5 first for simple terms
    is_simple = bool(re.match(r'^[\w\s]+$', pattern))
    if is_simple:
        prefix = uri.rstrip("/")
        # Add * for prefix matching so "qubit" matches "qubits"
        fts_query = " ".join(f'"{w}"*' for w in pattern.split() if w)
        fts_results = db.execute(
            "SELECT resource_uri, content, rank FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY rank LIMIT 50",
            (fts_query,),
        ).fetchall()
        for row in fts_results:
            if row[0].startswith(prefix) or row[0] == prefix:
                results.append({"uri": row[0], "snippet": row[1][:300], "score": round(-row[2], 4)})
    else:
        # Regex fallback
        flags = re.IGNORECASE if case_insensitive else 0
        prefix = uri.rstrip("/")
        rows = db.execute("SELECT resource_uri, chunk_index, content FROM chunks WHERE resource_uri LIKE ? || '%' OR resource_uri = ?", (prefix, prefix)).fetchall()
        for row in rows:
            if re.search(pattern, row[2], flags):
                results.append({"uri": row[0], "chunk_index": row[1], "snippet": row[2][:300]})

    return json.dumps(results)


@mcp_server.tool()
def ov_search(query: str, target_uri: str = "", limit: int = 10) -> str:
    """Hybrid search — 0.7 * semantic + 0.3 * FTS5, merged and ranked.

    Args:
        query: Natural language search query.
        target_uri: Scope search to a specific arcana:// URI prefix (optional).
        limit: Max number of results (default 10).
    """
    # Semantic scores
    sem_results = json.loads(ov_find(query, target_uri=target_uri, limit=limit * 2))
    # FTS scores
    fts_results = json.loads(ov_grep(uri=target_uri or "arcana://", pattern=query))

    # Normalize and merge
    merged: dict[str, dict] = {}
    if sem_results:
        max_sem = max(r["score"] for r in sem_results) or 1.0
        for r in sem_results:
            key = f"{r['uri']}:{r.get('chunk_index', 0)}"
            merged[key] = {"uri": r["uri"], "snippet": r["snippet"], "sem": r["score"] / max_sem, "fts": 0.0}

    if fts_results:
        max_fts = max(r.get("score", 1) for r in fts_results) or 1.0
        for r in fts_results:
            key = f"{r['uri']}:{r.get('chunk_index', 0)}"
            if key in merged:
                merged[key]["fts"] = r.get("score", 1) / max_fts
            else:
                merged[key] = {"uri": r["uri"], "snippet": r["snippet"], "sem": 0.0, "fts": r.get("score", 1) / max_fts}

    # Weighted combine
    results = []
    for v in merged.values():
        v["score"] = round(0.7 * v["sem"] + 0.3 * v["fts"], 4)
        results.append({"uri": v["uri"], "score": v["score"], "snippet": v["snippet"]})

    results.sort(key=lambda x: x["score"], reverse=True)
    return json.dumps(results[:limit])


@mcp_server.tool()
def ov_read(uri: str) -> str:
    """Read full content of a resource (concatenated chunks in order).

    Args:
        uri: arcana:// URI to read.
    """
    db = _get_db()
    rows = db.execute("SELECT content FROM chunks WHERE resource_uri = ? ORDER BY chunk_index", (uri,)).fetchall()
    if not rows:
        return json.dumps({"error": f"Not found: {uri}"})
    return "\n\n".join(row[0] for row in rows)


@mcp_server.tool()
def ov_add_memory(role: str, content: str) -> str:
    """Store a memory entry as a resource with embedding.

    Args:
        role: Memory role (e.g. 'user', 'assistant', 'system').
        content: The memory content to store.
    """
    db = _get_db()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    uri = f"arcana://memories/{role}_{ts}"

    chunks = _chunk_text(content)
    embeddings = _embed_texts(chunks)

    db.execute(
        "INSERT OR REPLACE INTO resources (uri, source_path, kind, metadata) VALUES (?, ?, ?, ?)",
        (uri, "", "memory", json.dumps({"role": role})),
    )
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        db.execute(
            "INSERT INTO chunks (resource_uri, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
            (uri, idx, chunk, _pack_embedding(emb)),
        )
    db.commit()
    return json.dumps({"uri": uri, "chunks": len(chunks)})


@mcp_server.tool()
def ov_mkdir(uri: str) -> str:
    """Create a directory at a arcana:// URI.

    Args:
        uri: arcana:// URI for the new directory.
    """
    db = _get_db()
    db.execute("INSERT OR IGNORE INTO directories (uri) VALUES (?)", (uri,))
    db.commit()
    return f"Created {uri}"


@mcp_server.tool()
def ov_mv(from_uri: str, to_uri: str) -> str:
    """Move/rename a resource.

    Args:
        from_uri: Source arcana:// URI.
        to_uri: Destination arcana:// URI.
    """
    db = _get_db()
    # Disable FK checks for the move, then re-enable
    db.execute("PRAGMA foreign_keys=OFF")
    db.execute("UPDATE chunks SET resource_uri = ? WHERE resource_uri = ?", (to_uri, from_uri))
    db.execute("UPDATE resources SET uri = ?, updated_at = datetime('now') WHERE uri = ?", (to_uri, from_uri))
    db.execute("UPDATE directories SET uri = ? WHERE uri = ?", (to_uri, from_uri))
    db.execute("PRAGMA foreign_keys=ON")
    db.commit()
    return f"Moved {from_uri} -> {to_uri}"
