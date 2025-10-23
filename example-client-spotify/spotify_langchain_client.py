"""
LangChain Client for Spotify MCP Server
Demonstrates automatic tool discovery and model-agnostic design
"""

import asyncio
import os
from enum import Enum
from typing import Any, Literal
from dotenv import load_dotenv
import json
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, create_model, Field, field_validator, SecretStr



# Load environment variables
load_dotenv()



# ============================================================================
# ENUMS: Define fixed choices for internal code
# ============================================================================

# Below is an enum for LLMProvider. It defines a fixed set of allowed values at the code level (akin to multiple choice).
class LLMProvider(Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    


# ============================================================================
# PYDANTIC MODELS: Validate external data (configs, MCP responses, etc.)
# ============================================================================    

class LLMConfig(BaseModel):
    """Configuration for LLM - validates settings from environment/config files"""
    provider: LLMProvider
    model_name: str | None = None
    temperature: float = Field(default=0, ge=0, le=2, description="Temperature must be between 0 and 2")
    api_key: str = Field(min_length=1, description="API key must not be empty")
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("API key cannot be empty or whitespace")
        return v
    
    
class MCPServerConfig(BaseModel):
    """Configuration for connecting to MCP server"""
    server_path: str = Field(description="Path to MCP server directory")
    command: str = Field(default="uv", description="Command to run the server")
    
    @field_validator('server_path')
    @classmethod
    def validate_server_path(cls, v: str) -> str:
        if not os.path.exists(v):
            raise ValueError(f"Server path does not exist: {v}")
        return v
    
    
class MCPToolSchema(BaseModel):
    """Schema for an MCP tool - validates tool metadata from MCP server"""
    name: str = Field(min_length=1, description="Tool name")
    description: str | None = Field(default=None, description="Tool description")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON schema for tool inputs")
    
    @field_validator('name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(f"Tool name must be alphanumeric with underscores/hyphens: {v}")
        return v
    

class MCPToolCall(BaseModel):
    """Request to call an MCP tool - validates arguments before sending to MCP"""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('tool_name')
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Tool name cannot be empty")
        return v
    

class MCPToolResponse(BaseModel):
    """Response from MCP tool - validates data coming back from MCP"""
    success: bool = True
    content: str | None = None
    error: str | None = None
    
    @field_validator('content', 'error')
    @classmethod
    def validate_content_or_error(cls, v: str | None, info) -> str | None:
        # Ensure we have either content or error, not both
        values = info.data
        if values.get('success') and not v and info.field_name == 'content':
            raise ValueError("Successful response must have content")
        if not values.get('success') and not v and info.field_name == 'error':
            raise ValueError("Failed response must have error message")
        return v
    
    
class AgentQuery(BaseModel):
    """User query to the agent - validates input"""
    query: str = Field(min_length=1, max_length=5000, description="User's question")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()
    

# ============================================================================
# PRE-DEFINED TOOL SCHEMAS: Explicit schemas for each MCP tool
# ============================================================================

# Define proper schemas for each MCP tool
class SpotifySearchArgs(BaseModel):
    """Arguments for SpotifySearch tool"""
    query: str = Field(description="Search query")
    qtype: str = Field(description="Type: track, artist, album, or playlist")
    limit: int | None = Field(default=10, description="Number of results")

class SpotifyPlaylistArgs(BaseModel):
    """Arguments for SpotifyPlaylist tool"""
    action: Literal["get", "get_tracks", "add_tracks", "remove_tracks", "change_details", "create"] = Field(
        description="Action to perform"
    )
    playlist_id: str | None = Field(default=None, description="Playlist ID")
    track_ids: list[str] | None = Field(default=None, description="List of track IDs")  # ← ARRAY from the start!
    name: str | None = Field(default=None, description="Playlist name")
    description: str | None = Field(default=None, description="Playlist description")
    public: bool | None = Field(default=True, description="Public playlist")

class SpotifyPlaybackArgs(BaseModel):
    """Arguments for SpotifyPlayback tool"""
    action: Literal["get", "start", "pause", "skip"] = Field(description="Playback action")
    spotify_uri: str | None = Field(default=None, description="Spotify URI to play")
    num_skips: int | None = Field(default=1, description="Number of tracks to skip")

class SpotifyGetInfoArgs(BaseModel):
    """Arguments for SpotifyGetInfo tool"""
    item_uri: str = Field(description="Spotify URI of item")

class SpotifyQueueArgs(BaseModel):
    """Arguments for SpotifyQueue tool"""
    action: Literal["get", "add"] = Field(description="Queue action")
    track_id: str | None = Field(default=None, description="Track ID to add")

# Mapping of tool names to their schemas
TOOL_SCHEMAS = {
    "SpotifySearch": SpotifySearchArgs,
    "SpotifyPlaylist": SpotifyPlaylistArgs,
    "SpotifyPlayback": SpotifyPlaybackArgs,
    "SpotifyGetInfo": SpotifyGetInfoArgs,
    "SpotifyQueue": SpotifyQueueArgs,
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_llm(config: LLMConfig):
    """
    Get LLM instance based on validated config (model-agnostic)
    
    Args:
        config: Validated LLM configuration with provider, model, etc.
    """
    
    if config.provider == LLMProvider.ANTHROPIC:
        model_name = config.model_name or "claude-sonnet-4-5-20250929"
        return ChatAnthropic(
            model_name=model_name,
            temperature=config.temperature,
            api_key=SecretStr(config.api_key),
            timeout=None,  # Add the "missing" optional params
            stop=None
        )
    elif config.provider == LLMProvider.OPENAI:
        model_name = config.model_name or "gpt-5-2025-08-07"
        return ChatOpenAI(
            model=model_name,
            temperature=config.temperature,
            api_key=SecretStr(config.api_key),
        )
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
    
    
async def call_mcp_tool(
    tool_call: MCPToolCall,
    server_params: StdioServerParameters
) -> MCPToolResponse:
    """
    Call MCP tool with Pydantic validation on input and output
    
    Args:
        tool_call: Validated tool call request
        server_params: Server connection parameters
        
    Returns:
        Validated tool response
    """
    try:
        # Connect to MCP Server
        async with stdio_client(server_params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                
                # Make the tool call
                result = await session.call_tool(
                    tool_call.tool_name,
                    arguments=tool_call.arguments
                    )
               
                # Extract and validate response from tool call
                if result and result.content:
                    content = str(result.content[0])
                    # print(f"running call_mcp_tool ... result is: {result} and result.content is: {content}")
                    
                    # Handle different content types
                    if hasattr(content, "text"):
                        # TextContent
                        content = str(content_item.text)  # type: ignore
                    elif hasattr(content, "data"):
                        # ImageContent or other binary content
                        content = f"[Binary content: {type(content).__name__}]"
                    else:
                        # Fallback for any other content type
                        content = str(content)
                    return MCPToolResponse(success=True, content=content)
                
                else:
                    print(f"running call_mcp_tool ... no content returned from tool call")
                    return MCPToolResponse(success=False, error="No content in response")
                    
    except Exception as e:
        # Return validated error response
        print(f"running call_mcp_tool ... try-except failed")
        return MCPToolResponse(success=False, error=str(e))
    

async def discover_mcp_tools(
    server_config: MCPServerConfig
) -> tuple[list[StructuredTool], StdioServerParameters]:
    """
    Connect to MCP server and automatically discover available tools with validation
    
    Args:
        server_config: Validated server configuration
        
    Returns:
        Tuple of (validated tools, server parameters)
    """
    print(f"\n🔍 Connecting to MCP server: {server_config.server_path}")
    
    # Configure connection to MCP server
    server_params = StdioServerParameters(
        command=server_config.command,
        args=["--directory", server_config.server_path, "run", "spotify-mcp"],
        env={k: v for k, v in os.environ.copy().items() if k != 'VIRTUAL_ENV'}  # Filter out VIRTUAL_ENV
    )
    
    # Connect to the MCP server
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to MCP server")
            
            # AUTOMATIC DISCOVERY with validation
            print("\n🔍 Discovering available tools...")
            mcp_tools_response = await session.list_tools()
            
            print(f"✅ Discovered {len(mcp_tools_response.tools)} tools:\n")
            
            # Convert and validate MCP tools
            langchain_tools = []
            
            for mcp_tool in mcp_tools_response.tools:
                # Validate tool schema with Pydantic
                try:
                    validated_tool = MCPToolSchema(
                        name=mcp_tool.name,
                        description=mcp_tool.description,
                        input_schema=mcp_tool.inputSchema or {}
                    )
                    
                    print(f"  📦 {validated_tool.name}")
                    print(f"     Description: {validated_tool.description}")
                    print(f"     Parameters: {list(validated_tool.input_schema.get('properties', {}).keys())}\n")
                         
                except Exception as e:
                    print(f"  ❌ Skipping invalid tool: {mcp_tool.name} - {e}\n")
                    continue
    
                # Get pre-defined schema for this tool
                args_schema = TOOL_SCHEMAS.get(validated_tool.name)
                
                if not args_schema:
                    print(f"     ⚠️  No pre-defined schema for {validated_tool.name}, skipping...\n")
                    continue
    
                # Create wrapper function with validation  
                def make_tool_function(tool_name: str, params: StdioServerParameters):
                    async def call_tool_wrapper(**kwargs: Any) -> str:
                        """Wrapper that validates input/output"""
                        print(f"[DEBUG] Tool: {tool_name}, Args: {kwargs}")
                        
                        tool_call = MCPToolCall(
                            tool_name=tool_name,
                            arguments=kwargs  # Already properly typed by Pydantic schema!
                        )
                        
                        response = await call_mcp_tool(tool_call, params)
                        
                        if response.success:
                            return response.content or "No content"
                        else:
                            return f"Error: {response.error}"
                    
                    return call_tool_wrapper
                
                # Create LangChain tool with pre-defined schema
                langchain_tool = StructuredTool.from_function(
                    coroutine=make_tool_function(validated_tool.name, server_params),
                    name=validated_tool.name,
                    description=validated_tool.description or f"Tool: {validated_tool.name}",
                    args_schema=args_schema,  # Use our pre-defined schema
                )
                
                langchain_tools.append(langchain_tool)
            
            return langchain_tools, server_params



async def run_agent_query(
    agent,
    query: AgentQuery,
    tools: list[StructuredTool]
) -> str:
    """
    Run a validated query through the agent
    
    Args:
        agent: The LangChain agent
        query: Validated user query
        tools: Available tools
    """
    # Invoke the agent
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=query.query)]
    })
    
    # Extract the final response
    messages = result.get("messages", [])
    if messages:
        return messages[-1].content
    return "No response"


async def main():
    """
    Main function demonstrating automatic tool discovery with Enum + Pydantic validation
    """
    print("=" * 60)
    print("SPOTIFY MCP + LANGCHAIN DEMONSTRATION")
    print("With Enum + Pydantic Validation")
    print("=" * 60)
    
    try:
        # STEP 1: Validate MCP Server Configuration
        print("\n📋 Validating MCP server configuration...")
        server_config = MCPServerConfig(
            server_path="./example-client-spotify/spotify-mcp",
            command="uv"
        )
        print("✅ Server configuration valid")
        
        # STEP 2: Automatically discover and validate tools
        tools, server_params = await discover_mcp_tools(server_config)
        
        # STEP 3: Validate LLM Configuration
        print("\n📋 Validating LLM configuration...")
        llm_config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name="claude-sonnet-4-5-20250929",
            temperature=0.7,
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )
        print("✅ LLM configuration valid")
        
        # STEP 4: Create agent with validated config
        print(f"\n🤖 Creating agent with {llm_config.provider.value}...")
        llm = get_llm(llm_config)
        
        # Create memory saver for conversation persistence
        memory = MemorySaver()
        agent = create_agent(
            llm, 
            tools,
            checkpointer=memory
            )
        print("✅ Agent created successfully with memory")
        
        # STEP 5: Run validated queries
        print("\n" + "=" * 60)
        print("RUNNING QUERIES")
        print("=" * 60)
        
        # Configuration for the conversation thread
        config: RunnableConfig = {"configurable": {"thread_id": "spotify_conversation_1"}}
        
        user_email= os.getenv('EMAIL_SPOTIFY', '')
        queries = [
            "Search for the song 'Bohemian Rhapsody' by Queen",
            "What are Taylor Swift's top tracks?",
            f"Take those songs and create a new Spotify playlist called 'Taylor Swift Top Hits for {user_email}'"
        ]
        
        for query_text in queries:
            print(f"\n\n🗣️  USER: {query_text}")
            print("-" * 60)
            
            try:
                # Validate query with Pydantic
                validated_query = AgentQuery(query=query_text)
                
                # Run the query, invoking agent with memory
                result = await agent.ainvoke(
                    {"messages": [HumanMessage(content=validated_query.query)]},
                    config=config  # Same config = same conversation thread
                )
                
                # Extract response
                messages = result.get("messages", [])
                if messages:
                    # Get the last AI message
                    for msg in reversed(messages):
                        if hasattr(msg, 'content') and msg.content:
                            print(f"\n✅ AGENT: {msg.content}")
                            break
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
    