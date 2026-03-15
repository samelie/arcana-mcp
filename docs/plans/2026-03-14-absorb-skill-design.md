# Absorb Skill Design

## Objective

A Claude Code skill (`/absorb <path>`) that traverses a target folder, generates knowledge files optimized for Claude retrieval via Arcana MCP, and indexes them. Knowledge is written by Claude, for Claude — not human documentation.

## Core value proposition

Cold-start Claude sessions waste 1-3 minutes exploring packages they've worked on before. Arcana stores persistent, semantically-searchable knowledge. But raw source files are poor knowledge artifacts — implementation noise buries the useful patterns. `/absorb` generates **operational briefings**: dense, structured knowledge that orients a future session in seconds via `ov_search`.

## Location

- Skill: `.claude/skills/context/absorb/SKILL.md`
- Output: `<target>/knowledge/` directory
- Arcana URI: `arcana://<package-name>/knowledge/*`

## Three-phase process

### Phase 0: Diff (re-runs only)

On repeat invocations:
1. Read existing `<target>/knowledge/*.md` files
2. Parse frontmatter `sources` list and `source_hash`
3. Hash current source files, compare
4. Flag files for regeneration (sources changed), removal (sources deleted), or skip (unchanged)
5. `ov_rm` stale Arcana entries before proceeding

Skip to Phase 2 for files that need no update.

### Phase 1: Survey

Explore agent maps the target folder:
- File tree (skip node_modules, .venv, dist, __pycache__, .git)
- Package identity (package.json or pyproject.toml — name, deps, scripts)
- Entry points and exports
- Test locations and run commands
- Existing knowledge/ files

Output: structured inventory held in working memory. Not written to disk.

### Phase 2: Synthesize

Read key files from the survey. Write knowledge files to `<target>/knowledge/`. Index each via `ov_add_resource`.

## Knowledge file format

### Frontmatter

```markdown
---
generated_at: 2026-03-14
source_hash: <sha256 of concatenated source file contents>
sources:
  - src/server.ts
  - src/db.ts
  - package.json
---
```

### Content

Dense, flat, no narrative. Headers map to Arcana's markdown chunker (~2000 char segments). Each section should stand alone as a retrievable chunk.

## Generation rubric

The skill does NOT enforce rigid document categories. It provides these questions as a rubric — Claude answers whichever are relevant, as densely as possible:

| Question | Purpose |
|----------|---------|
| What is this? 3-sentence mental model. | Instant orientation |
| Which files matter? Which are boilerplate? | Skip noise |
| Non-obvious cross-package relationships? | Prevent blind breaking changes |
| Where do conventions diverge from defaults? | Prevent wrong-pattern application |
| What breaks silently? Gotchas? | Prevent repeat mistakes |
| Build, test, deploy — exact commands? | Eliminate guessing |
| Data flow / request lifecycle? | Operational backbone |
| Patterns to follow when modifying? | Prevent inconsistencies |

## Output format principles

- Optimized for machine retrieval, not human reading
- Dense: no filler words, no explanatory prose
- Structured: aggressive headers so chunks are self-contained
- Actionable: commands, file paths, concrete patterns — not abstractions
- Honest: if something is unknown or unclear, say so — don't hallucinate

## Staleness management

1. **Source manifest in frontmatter** — `sources` + `source_hash` enable diff on re-run
2. **Full replace per file** — `ov_rm` old entry, `ov_add_resource` new one. No incremental patching.
3. **Deletion detection** — if source files no longer exist, remove the knowledge file and its Arcana entry
4. **Timestamp** — `generated_at` lets future sessions judge recency

## Re-runnability contract

- `/absorb <path>` is idempotent
- Running twice with no source changes produces no writes
- Running after source changes updates only affected knowledge files
- Running after source deletion removes orphaned knowledge

## Unresolved questions

- Max knowledge files per package? Or leave unbounded?
- Should the skill auto-run Arcana search after indexing to verify retrieval quality?
- Naming convention for knowledge files — by topic (`auth.md`, `data-flow.md`) or single `OVERVIEW.md`?
