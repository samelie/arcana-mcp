# arcana-mcp

Semantic vector DB as an MCP server for Claude Code — SQLite + FTS5 + local ONNX embeddings.

Gives Claude persistent, searchable project knowledge across conversations. Index files, store findings, search semantically — all through MCP tools.

## Install

### Claude Code Plugin (recommended)

```bash
claude plugin marketplace add samelie/arcana-mcp
claude plugin install arcana-mcp
```

This installs the MCP server, skills (`/arcana:arcana-search`, `/arcana:arcana-absorb`), command (`/arcana:search`), agent (`arcana-researcher`), and orientation protocol automatically.

### Manual

```bash
pip install arcana-mcp
```

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "arcana": {
      "command": "uvx",
      "args": ["arcana-mcp", "serve"]
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `arcana_add_resource` | Index a file or directory into the DB |
| `arcana_add_memory` | Store a memory entry with embedding |
| `arcana_search` | Hybrid semantic + FTS5 search (best default) |
| `arcana_find` | Pure semantic (cosine similarity) search |
| `arcana_grep` | Keyword/regex search via FTS5 |
| `arcana_read` | Read full content of a resource |
| `arcana_ls` | List direct children at a URI |
| `arcana_tree` | Show recursive tree at a URI |
| `arcana_stat` | Get metadata + chunk count for a resource |
| `arcana_rm` | Remove a resource (with optional recursive) |
| `arcana_mkdir` | Create a directory at a URI |
| `arcana_mv` | Move/rename a resource |

## Skills

### `/arcana:arcana-absorb <path>`
Generates knowledge files optimized for Claude retrieval. Surveys a directory, synthesizes structured knowledge, and indexes it into Arcana. Re-runnable — updates stale files, removes orphans.

### `/arcana:arcana-search`
Quick access to search, store, and browse project knowledge. Use `arcana_search` for hybrid search, `arcana_add_memory` for quick findings, `arcana_add_resource` for indexing files.

## Commands

### `/arcana:search <query>`
Quick-invoke search — runs `arcana_search` with the given query and returns results directly.

## Agents

### `arcana-researcher`
Lightweight agent for delegating knowledge searches to a subagent. Searches Arcana, reads top results, returns a focused summary. Keeps main conversation context clean.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ARCANA_DB_PATH` | `~/.arcana/context.db` | SQLite database path |
| `ARCANA_MODEL_CACHE` | `~/.arcana/models` | ONNX model cache directory |

## Architecture

- **SQLite + FTS5**: Full-text search with trigram tokenization
- **fastembed**: Local ONNX embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **Hybrid search**: 0.7 × semantic + 0.3 × FTS5 for best-of-both ranking
- **Markdown chunking**: Splits on `#` headings into ~2000 char segments
- **MCP transport**: stdio via FastMCP

## Releasing

From the monorepo root, commit and push your changes, then run:

```bash
# Release the current version in pyproject.toml
./packages/arcana-mcp/scripts/release.sh

# Or bump + release in one step
./packages/arcana-mcp/scripts/release.sh 0.2.0
```

The script will:
1. Validate you're on `main` with a clean tree
2. Optionally bump `pyproject.toml` and commit
3. Wait for the monorepo sync workflow to push to `samelie/arcana-mcp`
4. Verify the remote version matches
5. Create a GitHub release (`v0.x.x`) which triggers the PyPI publish workflow

## License

MIT
