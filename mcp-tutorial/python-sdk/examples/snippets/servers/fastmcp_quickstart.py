"""
FastMCP quickstart example.

To start the server in standalone (production) mode:
    cd to the `examples/snippets/clients` directory and run:
        uv run server fastmcp_quickstart stdio
        example: cd /home/thebuleganteng/01_Repos/06_personal_work/mcp-tutorial/python-sdk/examples/snippets/clients && uv run server fastmcp_quickstart stdio

Alternatively, to start the server in standalone (dev) mode with the inspector:
    uv run inspector <python file with desired server>
    example: cd /home/thebuleganteng/01_Repos/06_personal_work/mcp-tutorial/python-sdk/examples/snippets/servers && uv run mcp dev fastmcp_quickstart.py
    example: uv run mcp dev simple-tool/server.py
    example: uv run mcp dev simple-resource/server.py

"""

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."
