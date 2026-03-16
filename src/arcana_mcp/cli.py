"""CLI entry point: arcana-mcp <subcommand>."""

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path


def _copy_skills(dest: Path) -> list[str]:
    """Copy bundled skills to destination directory."""
    copied = []
    # In installed wheel, skills are at arcana_mcp/skills/
    skills_pkg = Path(resources.files("arcana_mcp").joinpath("skills"))

    if not skills_pkg.is_dir():
        # Fallback: development mode (skills/ is sibling to src/)
        skills_pkg = Path(__file__).resolve().parent.parent.parent / "skills"

    if not skills_pkg.is_dir():
        print(f"Warning: skills directory not found at {skills_pkg}", file=sys.stderr)
        return copied

    for skill_dir in skills_pkg.iterdir():
        if not skill_dir.is_dir():
            continue
        target = dest / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        copied.append(skill_dir.name)

    return copied


def _ensure_mcp_json(project_root: Path) -> bool:
    """Create or update .mcp.json with arcana entry."""
    mcp_path = project_root / ".mcp.json"
    config: dict = {}

    if mcp_path.exists():
        try:
            config = json.loads(mcp_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if "arcana" in config["mcpServers"]:
        return False

    config["mcpServers"]["arcana"] = {
        "command": "arcana-mcp",
        "args": ["serve"],
    }

    mcp_path.write_text(json.dumps(config, indent=2) + "\n")
    return True


CLAUDE_MD_SNIPPET = """\
## Project Context (Arcana)

Arcana is a semantic vector DB (SQLite + FTS5 + local ONNX embeddings) for project knowledge.
Use the `arcana_*` MCP tools directly — no skill invocation needed.

### Orientation protocol
When starting work on a package/feature you haven't touched in this session:
1. `arcana_search("<package or feature>")` — get architectural context BEFORE exploring code
2. If results are relevant, `arcana_read` the top hit for full context
3. Only then Grep/Glob actual source files for implementation details

### Searching
- `arcana_search` — hybrid semantic + keyword search (best default)
- `arcana_find` — pure semantic search (when keywords aren't enough)
- `arcana_grep` — exact pattern/regex matching within a URI scope
- `arcana_read` — full content of a specific resource

### Storing
- `arcana_add_memory(role="assistant", content="...")` — quick findings, gotchas
- `arcana_add_resource(path="<file>", to="arcana://<uri>")` — index files/directories
For significant discoveries, update knowledge files via `/absorb`.

### Browsing
- `arcana_ls` — list direct children at a URI
- `arcana_tree` — show full recursive tree
- `arcana_stat` — metadata + chunk count for a resource
"""


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize Arcana in the current project."""
    project_root = Path(args.project_dir).resolve()

    # 1. Copy skills
    skills_dest = project_root / ".claude" / "skills" / "arcana"
    skills_dest.mkdir(parents=True, exist_ok=True)
    copied = _copy_skills(skills_dest)

    # 2. Update .mcp.json
    created = _ensure_mcp_json(project_root)

    # 3. Print summary
    print("arcana-mcp init complete!\n")
    if copied:
        print(f"  Skills installed: {', '.join(copied)}")
        print(f"    → {skills_dest}/")
    if created:
        print("  .mcp.json updated with arcana server entry")
    else:
        print("  .mcp.json already has arcana entry (skipped)")

    print("\n  Add this to your CLAUDE.md:\n")
    for line in CLAUDE_MD_SNIPPET.splitlines():
        print(f"    {line}")
    print()


def cmd_serve(_args: argparse.Namespace) -> None:
    """Run the MCP server."""
    from .server import mcp_server

    mcp_server.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(prog="arcana-mcp", description="Semantic vector DB as an MCP server")
    sub = parser.add_subparsers(dest="command")

    serve_parser = sub.add_parser("serve", help="Run MCP server (stdio transport)")
    serve_parser.set_defaults(func=cmd_serve)

    init_parser = sub.add_parser("init", help="Initialize Arcana in a project")
    init_parser.add_argument("--project-dir", default=".", help="Project root directory (default: current dir)")
    init_parser.set_defaults(func=cmd_init)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        # Default to serve for backwards compat with .mcp.json configs
        cmd_serve(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
