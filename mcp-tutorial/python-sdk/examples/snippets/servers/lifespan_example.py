"""Example showing lifespan support for startup/shutdown with strong typing."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

'''
Notes re this example: 

    - The Database Connection:
        The example creates a mock database connection that:
            - Connects when the server starts
            - Stays connected while the server runs
            - Disconnects cleanly when the server stops

    - The AppContext:
        - This is a typed container that holds your initialized resources (like the database). It ensures type-safe access throughout your code.

    Key learnings:
        - Running the query_db Tool via the inspector uses the database connection established during startup and runs the query method of the Database class (which, in this example, just returns a string).
        - The lifespan context is accessible in any Tool or endpoint via the Context object, ensuring type safety and easy access to shared resources.
'''


# Mock database class for example
class Database:
    """Mock database class for example."""

    @classmethod
    async def connect(cls) -> "Database":
        """Connect to database."""
        return cls()

    async def disconnect(self) -> None:
        """Disconnect from database."""
        pass

    def query(self) -> str:
        """Execute a query."""
        return "Query result"


@dataclass
class AppContext:
    """
    - Application context with typed dependencies.
    - This says: "AppContext will always contain a db attribute, and it will always be of type Database (defined above)."
    - If we wanted to add more resources, we could just add more attributes here. 
        Example: 
            class AppContext:
                db: Database
                cache: RedisCache | None = None  # Optional - defaults to None
                config: AppConfig | None = None  # Optional - defaults to None
        In this case, we would update the yield statement in app_lifespan to include these new attributes.
            Example:
                yield AppContext(db=db, cache=cache, config=config)
    """
    db: Database


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Manage application lifecycle with type-safe context.
    
    Key concepts: 
        - The -> AsyncIterator[AppContext] part tells Python: "This function will yield an AppContext object."
        - This function doesn't return - it yields. This is important because:
            - return gives you something once and the function ends
            - yield gives you something, pauses, waits, and then continues
        - When we call app_lifespan, it will:
            1. Run the code before yield (initialize resources)
            2. Pause and give the AppContext (containing a db attribute via AppContext.db) to the server
            3. Server runs - tools can now access the database via ctx.request_context.lifespan_context.db
            4. When server shuts down, resume from the yield and run the finally block (cleanup - disconnect database)
    """
    # Initialize on startup
    db = await Database.connect()
    try:
        yield AppContext(db=db)
        # Function pauses here while server runs
    finally:
        # Cleanup on shutdown
        await db.disconnect()


# Pass lifespan to server
"""
Key concepts:
    - This effectively says: 
        "When you start the server, execute the app_lifespan function to set up resources."
"""
mcp = FastMCP("My App", lifespan=app_lifespan)


# Access type-safe lifespan context in tools
"""
Key concepts:
    - @mcp.tool() is a decorator that registers the function below (query_db) as a Tool in the "mcp" FastMCP server created above.
    - Function signature comments:
        - Context:
            - a generic type that provides access to both the current server session and the application context (which includes our database connection).
            - contains three type parameters:
                1. ServerSessionT: 
                    (1a) (in this example, ServerSessionT= ServerSession)
                    (1b) must come first
                    (1c) imported as part of the mcp library
                    (1d) Access via: ctx.session
                2. LifespanContextT
                    (2a) (in this example, LifespanContextT= AppContext)
                    (2b) must come second
                    (2c) Access via: ctx.request_context.lifespan_context
                3. RequestT (optional)
                    (3a) (not used in this example)
                    (3b) must come last if used
                    (3c) Access via: ctx.request_context.request
    - The example below basically says the following:
        1. db = ctx.request_context.lifespan_context.db --> "Get the database object (i.e. database connection) that was created once at server startup and stored in the lifespan context."
        2. return db.query() --> "Run the query method on that database object and return the result."
"""
@mcp.tool() 
def query_db(ctx: Context[ServerSession, AppContext]) -> str:
    """Query the database using the lifespan context."""    
    db = ctx.request_context.lifespan_context.db
    return db.query()
