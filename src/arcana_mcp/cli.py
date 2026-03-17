"""CLI entry point: arcana-mcp serve."""

import argparse


def cmd_serve(_args: argparse.Namespace) -> None:
    """Run the MCP server."""
    from .server import mcp_server

    mcp_server.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(prog="arcana-mcp", description="Semantic vector DB as an MCP server")
    sub = parser.add_subparsers(dest="command")

    serve_parser = sub.add_parser("serve", help="Run MCP server (stdio transport)")
    serve_parser.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        # Default to serve for backwards compat with .mcp.json configs
        cmd_serve(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
