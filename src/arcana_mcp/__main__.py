from .server import mcp_server


def main():
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
