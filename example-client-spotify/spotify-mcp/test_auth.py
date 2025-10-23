import asyncio
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def test_auth():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "spotify-mcp"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("Initialized successfully")
            
            # Call search - this should trigger OAuth
            result = await session.call_tool(
                "SpotifySearch",
                arguments={"query": "test", "qtype": "track", "limit": 1}
            )
            print("Search result:", result)

if __name__ == "__main__":
    asyncio.run(test_auth())
