---
name: arcana-absorb
description: "Traverse a folder, generate knowledge files optimized for Claude retrieval via Arcana, and index them. Triggers: absorb, generate knowledge, index knowledge, build knowledge base, learn this package, absorb folder"
---

# /arcana-absorb <target_path>

Generate persistent, semantically-searchable knowledge for a target folder. Knowledge is written by Claude, for Claude — not human documentation. Output goes to `<target>/knowledge/`, indexed into Arcana via `arcana_add_resource`.

Re-runnable: updates stale knowledge, removes orphaned entries, skips unchanged files.

## Phase -1: Check existing
Run `arcana_search("<package name>")` to see what's already indexed. Read top results. Use as baseline — update/extend, don't overwrite with redundant info.

## Phase 0: Diff (re-runs only)

Skip this phase if `<target>/knowledge/` doesn't exist or is empty.

1. Read all `<target>/knowledge/*.md` files
2. Parse frontmatter: `sources` list and `source_hash`
3. Compute current hash of each source file listed (sha256 of concatenated contents)
4. Classify each knowledge file:
   - **unchanged**: hash matches → skip entirely
   - **stale**: hash differs or new source files appeared → regenerate
   - **orphaned**: all source files deleted → delete knowledge file + `arcana_rm` its Arcana entry
5. For stale files, `arcana_rm` the existing Arcana entry before proceeding

## Phase 1: Survey

Explore and map the target folder. Capture:

- File tree (skip: node_modules, .venv, dist, __pycache__, .git, *.lock)
- Package identity: name, version, description from package.json / pyproject.toml
- Entry points and public exports
- Dependencies (internal project deps are most important)
- Test locations and exact run commands
- Scripts / build commands
- Build configs: read tsup.config.ts, vite.config.ts, Dockerfile, pyproject.toml [build-system]
- Deployment configs: read docker-compose.yaml, Caddyfile, nginx.conf, pulumi index.ts, etc.
- Existing knowledge/ files (for context on what's already documented)

Hold the inventory in working memory. Do not write to disk.

## Phase 2: Synthesize

Read the key files identified by the survey. Generate knowledge files in `<target>/knowledge/`.

### What to write

You decide the number and topic of knowledge files based on the package's complexity. A small utility might need one file. A full-stack app might need several. Do NOT enforce rigid categories.

Use this rubric — answer whichever questions are relevant, as densely as possible:

**Orientation**
- What is this? 3-sentence mental model that makes everything else click.
- Which files/modules actually matter? Which are boilerplate to skip?
- REQUIRED in overview.md: a "Files that matter vs boilerplate" section listing the 5-10 key entry points vs directories to skip.

**Relationships**
- How does this connect to other packages in the project? Shared types, API boundaries, build order.
- Non-obvious dependencies — "changing X here breaks Y over there silently."
- If the target has >3 sub-packages/modules, REQUIRED: write a dedicated `cross-package-data-flow.md` with:
  - Request lifecycles (trace a user action through all layers)
  - Breaking change propagation table (Change → Affected systems)
  - Dependency graph (ASCII or mermaid)

**Operations**
- Exact build, test, lint, deploy commands. No guessing.
- Data flow / request lifecycle — the operational backbone.
- Environment requirements, secrets, config.
- Test topology: for each sub-project, where tests live and how to run them. Explicitly note when a sub-project has NO tests.
- Step-by-step guides for common modifications ("How to add a new X") — but only for entities with >3 touch points. Trivial additions don't need guides.

**Pitfalls**
- What breaks silently? What are the gotchas?
- Where do conventions diverge from what you'd assume by default?
- Patterns that MUST be followed when modifying (and why).
- Capture implementation constants a future session would waste time rediscovering: magic numbers, port numbers, timeout intervals, auth token claims, regex patterns, routing rules, polling intervals.

**History** (only if discoverable from code/comments/git)
- Why do certain patterns exist? What past mistakes led to current conventions?

### How to write it

<CRITICAL>
This is NOT documentation for humans. This is operational briefing material for a cold-start Claude session that needs to be effective in this package immediately.

- Dense. No filler words, no explanatory prose, no "this section covers..."
- Structured. Use headers aggressively — Arcana's markdown chunker splits on `#` headings into ~2000 char segments. Each section must stand alone as a retrievable chunk.
- Actionable. File paths, commands, concrete patterns. Not abstractions.
- Honest. If something is unclear or unknown, say so. Never fabricate.
- Flat. No nested sub-sub-sections. H2 is the primary unit.
- Queryable headings. Headings should BE the query someone would type. "Adding a new API endpoint" not "API Endpoints". "Why Redis instead of Memcached" not "Caching Layer". Test: if a heading could apply to any project, it's too generic.

ANTI-PATTERNS:
- Generic headings like "Architecture", "Overview", "Configuration" — these compete with every other package's knowledge in semantic search. Use specific headings: "Express middleware execution order", not "Architecture".
- Sections that assume reading order. Each H2 chunk may be retrieved in isolation. Include enough context that the chunk makes sense standalone.
</CRITICAL>

### File format

Every knowledge file must have this frontmatter:

```markdown
---
generated_at: YYYY-MM-DD
source_hash: <sha256 of concatenated source file contents, hex, first 8 chars>
sources:
  - <relative paths from target root>
---
```

### Naming

Name files by topic: `overview.md`, `data-flow.md`, `gotchas.md`, etc. Use lowercase-kebab-case. The filename should be meaningful for Arcana URI construction (`arcana://<pkg>/knowledge/<filename>`).

## Phase 3: Index

For each knowledge file written or updated:

```
arcana_add_resource(
  path="<absolute path to knowledge file>",
  to="arcana://<package-name>/knowledge/<filename-without-ext>",
  reason="<one-line description of what this knowledge covers>"
)
```

Use the package name from package.json/pyproject.toml (e.g., `my-backend` → `my-backend`).

## Phase 4: Verify

Run `arcana_search` with 2-3 queries that a future session would plausibly ask about this package. Confirm the new knowledge surfaces in top results. If not, review chunk boundaries and adjust headers.

## Re-run contract

- Idempotent: running twice with no source changes produces no writes
- Stale: source changes trigger regeneration of affected knowledge files only
- Orphaned: deleted sources trigger removal of knowledge files + Arcana entries
- Additive: new source files may trigger new knowledge files without affecting existing ones
