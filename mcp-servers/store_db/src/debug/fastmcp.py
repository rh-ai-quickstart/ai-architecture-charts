import asyncio

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MinimalTest")


@mcp.tool()
async def simple_async_tool() -> str:
    await asyncio.sleep(0.01)  # Small await
    return "Hello from minimal tool"


if __name__ == "__main__":
    print("Starting minimal FastMCP server on port 8001 (SSE)...")
    mcp.settings.port = 8002
    mcp.run(transport="sse")
