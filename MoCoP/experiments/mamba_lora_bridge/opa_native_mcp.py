import sys
import subprocess
import os
import asyncio
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# A clean, low-level MCP server implementation to guarantee zero ASCII/logging pollution on stdout.
server = Server("opa-native")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="shell",
            description="Executes a powershell command on Opa-PC and returns stdout.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command string to execute"}
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="read_file",
            description="Reads a text file from Opa-PC given its absolute path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="list_directory",
            description="Returns a list of files and folders in the given directory on Opa-PC.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "shell":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", arguments["command"]],
                capture_output=True, text=True, check=True
            )
            return [TextContent(type="text", text=result.stdout)]
        except subprocess.CalledProcessError as e:
            return [TextContent(type="text", text=f"Error executing command:\nSTDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")]
    
    elif name == "read_file":
        try:
            with open(arguments["path"], 'r', encoding='utf-8', errors='ignore') as f:
                return [TextContent(type="text", text=f.read())]
        except Exception as e:
            return [TextContent(type="text", text=str(e))]
            
    elif name == "list_directory":
        try:
            items = os.listdir(arguments["path"])
            return [TextContent(type="text", text="\n".join(items))]
        except Exception as e:
            return [TextContent(type="text", text=str(e))]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)

if __name__ == "__main__":
    asyncio.run(main())
