from mcp_server.server import mcp

if __name__ == "__main__":
    from mcp_server.db import get_db

    get_db()
    mcp.run()
