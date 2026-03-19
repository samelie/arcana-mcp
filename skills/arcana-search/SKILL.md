---
name: arcana-search
description: "Search, store, browse, or index project knowledge in Arcana (the project's semantic vector DB). Use this skill whenever the user asks what we know about a package or feature, wants to remember/save a finding or gotcha for future sessions, asks to search arcana or the knowledge base, wants to see what's indexed (browse/tree), asks about documented gotchas or conventions, says 'save that somewhere' or 'don't forget this', wants to index a directory into arcana, or asks about project knowledge. Also use proactively after long debugging sessions to store root causes. Do NOT use for code search (grep/glob), git history, generating knowledge files (use /arcana:arcana-absorb instead), or when 'context' refers to React Context, CSS context menus, or type names like CalcContext/ExecutionContext."
---

# /arcana:arcana-search

## Store context
When discovering a notable pattern, bug, gotcha, architecture decision, or convention:
1. Use `arcana_add_memory` with role="assistant" and the context as content
2. For files/directories, use `arcana_add_resource` with the path
3. Verify storage with `arcana_find`

## Search context
When starting work on a topic or answering project questions:
1. Use `arcana_search` for hybrid semantic+keyword search
2. Use `arcana_find` for pure semantic search
3. Use `arcana_grep` for exact pattern/regex matching within a URI scope
4. Use `arcana_read` for full content of a specific resource

## Deep research
When you need comprehensive understanding of a topic before acting:
1. Start broad: `arcana_search("<main topic>")` — scan all results
2. Read top 2-3 hits: `arcana_read` each for full content
3. Extract subtopics: from those results, identify related concepts, packages, data flows mentioned
4. Follow-up searches: `arcana_search` for each subtopic (2-4 queries)
5. Read new high-scoring results that add information not yet seen
6. Stop at saturation: when searches return chunks you've already read
7. Summarize what you know before proceeding to code exploration

Use deep research when:
- Starting work on an unfamiliar package
- Debugging across package boundaries
- Planning a change that touches multiple systems
- The user says "use Arcana to understand X"

## Add project resources
To index project docs, repos, or code:
1. Use `arcana_add_resource` with the file/directory path
2. Optionally set `to` for a custom arcana:// URI

## Auto-trigger conditions
Store context automatically (without user prompting) when:
1. A debugging session took 5+ tool calls to resolve — store root cause
2. A discovered pattern contradicts or supplements existing Arcana knowledge
3. A new gotcha/constraint found that would trap a future cold-start session

## Browse the context tree
- `arcana_ls` — list direct children at a URI
- `arcana_tree` — show full recursive tree
- `arcana_stat` — get metadata + chunk count for a resource
