import sys
from winremote_mcp.main import create_mcp

if __name__ == "__main__":
    mcp = create_mcp()
    mcp.run(transport="stdio")
