import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def run():
    url = "http://192.168.2.194:8090/sse"
    print(f"Connecting to {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            print("Initializing session...")
            await session.initialize()
            print("Session initialized!")
            
            # List available tools just to be sure
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"Available tools: {len(tool_names)}")
            
            if "Shell" in tool_names:
                print("Executing 'Shell' tool with command 'start powershell'...")
                result = await session.call_tool("Shell", {"command": "start powershell"})
                print(f"Result: {result.content}")
            else:
                print("'Shell' tool not found!")

if __name__ == "__main__":
    asyncio.run(run())
