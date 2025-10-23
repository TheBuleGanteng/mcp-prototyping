# MCP Tutorial - Learning the Model Context Protocol

## Purpose

This document serves as a guide for understanding and working with the Model Context Protocol (MCP) examples in this repository. It provides:

- Instructions for running MCP servers in different modes
- Detailed explanations of what each example demonstrates
- Step-by-step walkthroughs of key concepts

This is a learning resource created while exploring the MCP Python SDK examples.

## Prerequisites

- Python 3.10 or higher
- `uv` package manager installed
- Basic understanding of Python async/await

## Running MCP Servers

### Development Mode (MCP Inspector)

The MCP Inspector provides a web-based interface for testing and debugging your MCP server.

**To start a server with the Inspector:**

```bash
cd /path/to/python-sdk/examples/snippets/servers
uv run mcp dev <filename>.py
```

**Example:**
```bash
cd /home/thebuleganteng/01_Repos/06_personal_work/mcp-tutorial/python-sdk/examples/snippets/servers
uv run mcp dev lifespan_example.py
```

This will:
1. Start the MCP server
2. Launch the Inspector web interface in your browser
3. Allow you to interactively test tools, resources, and prompts

### Production/Standalone Mode

To run a server directly without the Inspector:

```bash
python <filename>.py
```

Or using `uv`:
```bash
uv run mcp run <filename>.py
```

### Claude Desktop Integration

To install a server for use with Claude Desktop:

```bash
uv run mcp install <filename>.py
```

Optional flags:
- `--name "Custom Name"` - Set a custom server name
- `-v KEY=value` - Set environment variables
- `-f .env` - Load environment variables from a file

## Example Files

### lifespan_example.py

**Location:** `python-sdk/examples/snippets/servers/lifespan_example.py`

**What it demonstrates:**
- Resource lifecycle management (startup/shutdown)
- Type-safe application context
- Sharing resources across multiple tool calls

**Key Concepts:**

#### 1. Resource Lifecycle Management

The lifespan pattern manages resources that should exist for the entire server lifetime:

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    # Startup: Initialize resources
    db = await Database.connect()
    try:
        # Yield resources for use during server lifetime
        yield AppContext(db=db)
        # Server runs here (paused at yield)
    finally:
        # Shutdown: Clean up resources
        await db.disconnect()
```

**Lifecycle phases:**
1. **Startup** (before yield): Connect to database, initialize resources
2. **Running** (paused at yield): Server operates, tools can access resources
3. **Shutdown** (after yield): Disconnect, clean up

#### 2. Type-Safe Application Context

The `AppContext` class defines what resources are available:

```python
@dataclass
class AppContext:
    db: Database
```

This provides:
- Type safety (IDE autocomplete, type checking)
- Clear documentation of available resources
- Easy extension (add more resources as needed)

**Example with multiple resources:**
```python
@dataclass
class AppContext:
    db: Database
    cache: RedisCache | None = None  # Optional
    config: AppConfig | None = None  # Optional
```

#### 3. Accessing Lifespan Resources in Tools

Tools access lifespan resources through the `Context` object:

```python
@mcp.tool()
def query_db(ctx: Context[ServerSession, AppContext]) -> str:
    # Access the shared database connection
    db = ctx.request_context.lifespan_context.db
    return db.query()
```

**Understanding the Context type:**

`Context[ServerSession, AppContext]` has three type parameters:

| Parameter | Type in Example | Access Path | Purpose |
|-----------|----------------|-------------|---------|
| `ServerSessionT` | `ServerSession` | `ctx.session` | MCP session for communication |
| `LifespanContextT` | `AppContext` | `ctx.request_context.lifespan_context` | Your lifespan resources |
| `RequestT` (optional) | `Request` | `ctx.request_context.request` | HTTP request (rarely needed) |

**Key Points:**

- The database connection is created **once** at startup
- The **same** connection is shared across all tool calls
- Each query fetches **current** data (connection stays open, data is always fresh)
- Resources are cleaned up **once** at shutdown

#### 4. How to Test

1. Start the inspector:
   ```bash
   cd python-sdk/examples/snippets/servers
   uv run mcp dev lifespan_example.py
   ```

2. In the Inspector UI:
   - Click on the **Tools** tab
   - Select the `query_db` tool
   - Click **Run Tool** (no parameters needed)
   - Observe the result: `"Query result"`

3. Check the server logs to see:
   - Database connection at startup
   - Tool execution
   - Database disconnection at shutdown

**Learning Outcomes:**

After understanding this example, you should know:
- ✅ How to initialize resources that persist for the server's lifetime
- ✅ How to define type-safe contexts with `@dataclass`
- ✅ How to access lifespan resources in tools via `Context`
- ✅ The difference between connection (persistent) and data (always current)
- ✅ How the three-phase lifecycle (startup/running/shutdown) works

---

## Common Patterns and Gotchas

### The Context Access Path

The asymmetry in accessing Context attributes is confusing but intentional:

- `ctx.session` - Shortcut for `ServerSession` (used frequently)
- `ctx.request_context.lifespan_context` - Full path for your `AppContext` (no shortcut)

**Tip:** Create your own shortcut in tool functions:
```python
@mcp.tool()
def my_tool(ctx: Context[ServerSession, AppContext]) -> str:
    app_ctx = ctx.request_context.lifespan_context  # Shortcut
    db = app_ctx.db
    config = app_ctx.config
    # ... rest of function
```

### Generic Types and Type Parameters

Python's generic system uses **positional** parameters, not named ones:

```python
Context[ServerSession, AppContext]
        ↑              ↑
     Position 1    Position 2
```

You cannot write `Context[session=ServerSession, ...]` - generics don't support named parameters.

To understand what each position means, you must:
1. Read the documentation
2. Look at the class source code
3. Follow examples

### The @dataclass Decorator

`@dataclass` automatically generates an `__init__` method:

```python
@dataclass
class AppContext:
    db: Database
    cache: RedisCache
```

Is equivalent to:

```python
class AppContext:
    def __init__(self, db: Database, cache: RedisCache):
        self.db = db
        self.cache = cache
```

This saves you from writing boilerplate code!

---

## Troubleshooting

### "Context is not available outside of a request"

This error occurs when trying to access `ctx` properties outside a tool/resource function. The context only exists during request handling.

### "Module not found" errors

Make sure you're in the correct directory and using `uv run`:
```bash
cd python-sdk/examples/snippets/servers
uv run mcp dev <filename>.py
```

### Inspector not opening

Check that port 6274 (default) is not already in use. The inspector should automatically open in your browser at `http://localhost:6274`.

---

## Next Steps

After mastering `lifespan_example.py`, explore:

1. `basic_tool.py` - Simple tool creation
2. `basic_resource.py` - Resource patterns
3. `basic_prompt.py` - Prompt templates
4. `structured_output.py` - Working with typed outputs

Each example builds on concepts from previous ones.