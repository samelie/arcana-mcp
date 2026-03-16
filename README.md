# arcana-mcp

Semantic vector DB as an MCP server for Claude Code — SQLite + FTS5 + local ONNX embeddings.

Gives Claude persistent, searchable project knowledge across conversations. Index files, store findings, search semantically — all through MCP tools.

## Install

```bash
pip install arcana-mcp
```

## Quick Start

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "arcana": {
      "command": "arcana-mcp",
      "args": ["serve"]
    }
  }
}
```

Or use the init command to set everything up:

```bash
arcana-mcp init
```

This will:
1. Copy bundled skills (`/absorb`, `/context`) to `.claude/skills/arcana/`
2. Add the MCP server entry to `.mcp.json`
3. Print a CLAUDE.md snippet for the orientation protocol

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

### `/absorb <path>`
Generates knowledge files optimized for Claude retrieval. Surveys a directory, synthesizes structured knowledge, and indexes it into Arcana. Re-runnable — updates stale files, removes orphans.

### `/context`
Quick access to search, store, and browse project knowledge. Use `arcana_search` for hybrid search, `arcana_add_memory` for quick findings, `arcana_add_resource` for indexing files.

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

## CLAUDE.md Snippet

Add this to your project's `CLAUDE.md` for the orientation protocol:

```markdown
## Project Context (Arcana)

Arcana is a semantic vector DB for project knowledge. Use `arcana_*` MCP tools directly.

### Orientation protocol
When starting work on a package/feature you haven't touched in this session:
1. `arcana_search("<package or feature>")` — get context BEFORE exploring code
2. If results are relevant, `arcana_read` the top hit for full context
3. Only then Grep/Glob actual source files for implementation details
```

## License

MIT
