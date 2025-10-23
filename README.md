# MCP Prototype Repository

## Purpose

This repository demonstrates the creation and use of **Model Context Protocol (MCP)** implementations, showcasing both server and client architectures. It provides practical examples of:

- Building MCP servers that expose tools and functionality
- Creating MCP clients that integrate with LLMs (OpenAI/Anthropic) to consume MCP servers
- Understanding the MCP protocol through annotated examples and tutorials

---

## Prerequisites

- Python 3.10 or higher
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/))
- Spotify Developer Account with API credentials
- Anthropic API key (for Claude) and/or OpenAI API key

---

## Repository Structure

The repository contains three major components:

### 1. `example-client-spotify/` - MCP Client Implementation

**What is it:**  
An interactive MCP client that integrates with Anthropic Claude (or OpenAI) to interact with a Spotify MCP server. Demonstrates:
- Automatic tool discovery from MCP servers
- LangChain agent integration with conversation memory
- Multi-turn conversations with context persistence
- Type-safe tool invocation with Pydantic validation

**How to use it:**

1. **Setup environment variables**  
   Create a `.env` file in the root directory:
   ```bash
   # Spotify API Credentials
   SPOTIPY_CLIENT_ID=your_spotify_client_id
   SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
   SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
   
   # LLM API Key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   # Or use OpenAI:
   # OPENAI_API_KEY=your_openai_api_key
   
   # Optional: Your Spotify email for personalization
   EMAIL_SPOTIFY=your_email@example.com
   ```

2. **Configure Spotify Developer App**
   - Go to https://developer.spotify.com/dashboard
   - Create an app or use existing
   - Add `http://127.0.0.1:8888/callback` to Redirect URIs
   - Copy Client ID and Secret to `.env`

3. **Install dependencies**
   ```bash
   cd mcp-mvp
   uv sync
   ```

4. **Run the interactive client**
   ```bash
   uv run python example-client-spotify/spotify_langchain_client_v2.py
   ```

5. **Interact with the agent**
   - Type natural language queries about Spotify
   - Agent remembers context across messages
   - Type `quit`, `exit`, or `q` to end

**Expected Output:**
- Interactive terminal chat interface
- Real-time tool calls to Spotify API (search, create playlists, etc.)
- Results displayed in terminal
- Changes reflected in your Spotify account (playlists created, etc.)

**Example Interaction:**
```
🗣️  YOU: What are Taylor Swift's top tracks?
🤖 AGENT: [Lists Taylor Swift's popular songs with IDs]

🗣️  YOU: Create a playlist called "My Favorites" with those songs
🤖 AGENT: [Creates playlist and adds tracks]
✅ Playlist created in your Spotify account!
```

---

### 2. `example-server/spotify_mcp.py` - Custom MCP Server

**What is it:**  
A custom-built MCP server for Spotify that exposes tools for:
- Searching tracks, albums, artists, playlists
- Getting detailed information about Spotify items
- Retrieving audio features (tempo, key, energy, etc.)
- Getting personalized recommendations

This demonstrates how to build an MCP server from scratch using the `fastmcp` framework.

**How to use it:**

1. **Setup environment variables** (same as client above)

2. **Install dependencies**
   ```bash
   cd mcp-mvp
   uv sync
   ```

3. **Run with MCP Inspector** (for testing)
   ```bash
   cd example-server
   uv run mcp dev spotify_mcp.py
   ```
   This opens a web interface at `http://localhost:6274` for testing tools interactively.

4. **Run standalone** (for production)
   ```bash
   uv run python example-server/spotify_mcp.py
   ```

**Expected Output:**
- MCP Inspector web interface (in dev mode)
- Server runs and waits for stdio input (in standalone mode)
- Tool call results printed to terminal
- JSON-RPC messages exchanged via stdio

**Available Tools:**
- `search_tracks` - Search for tracks on Spotify
- `get_artist_info` - Get artist details, popularity, genres, top tracks
- `get_audio_features` - Get tempo, key, energy, danceability for a track
- `get_recommendations` - Get similar tracks based on seed tracks

---

### 3. `mcp-tutorial/` - Annotated MCP Examples

**What is it:**  
A cloned and enhanced version of the official Model Context Protocol repository from https://github.com/modelcontextprotocol/python-sdk with additional:
- Detailed logging and debug output
- Comprehensive docstrings explaining each concept
- Annotated code examples
- Custom README documentation

**How to use it:**

1. **Navigate to the tutorial directory**
   ```bash
   cd mcp-tutorial/python-sdk/examples/snippets/servers
   ```

2. **Run examples with MCP Inspector**
   ```bash
   uv run mcp dev <example_file>.py
   ```
   
   Examples to try:
   - `lifespan_example.py` - Resource lifecycle management
   - `basic_tool.py` - Simple tool creation
   - `basic_resource.py` - Resource patterns
   - `basic_prompt.py` - Prompt templates
   - `structured_output.py` - Typed outputs

3. **Follow the tutorial README**
   - See `mcp-tutorial/README.md` for detailed walkthroughs
   - Each example has explanations of key concepts
   - Common patterns and gotchas documented

**Expected Output:**
- MCP Inspector opens in browser (`http://localhost:6274`)
- Interactive testing interface for tools/resources/prompts
- Console logs showing server lifecycle events
- Detailed debug output for understanding MCP concepts

**Learning Path:**
1. Start with `lifespan_example.py` to understand resource management
2. Progress through `basic_tool.py`, `basic_resource.py`, `basic_prompt.py`
3. Review the annotated README for conceptual explanations
4. Experiment with modifications to deepen understanding

---

## Key Concepts Demonstrated

### MCP Architecture
- **Server**: Exposes tools, resources, and prompts via stdio/HTTP
- **Client**: Discovers and invokes server capabilities
- **Protocol**: Standardized JSON-RPC communication

### Tool Discovery
- Clients call `list_tools()` to discover available functionality
- No hardcoding - tools are discovered at runtime
- Schema-based validation ensures type safety

### Conversation Memory
- LangGraph's `MemorySaver` enables context persistence
- Agent remembers previous messages in the conversation
- Multi-turn interactions reference earlier context

### Type Safety
- Pydantic models validate all inputs/outputs
- Enums provide compile-time tool selection safety
- Schema definitions prevent runtime errors

---

## Troubleshooting

### OAuth Authentication Issues
- Ensure redirect URI in Spotify Dashboard exactly matches `.env`
- Use `http://127.0.0.1:8888/callback` (not `localhost`)
- Complete OAuth flow in browser when prompted

### Port Already in Use
- Kill existing processes: `lsof -i :8888` then `kill <PID>`
- Or change port in both `.env` and Spotify Dashboard

### Virtual Environment Warnings
- These are harmless - `uv` automatically uses correct venv
- To suppress: don't set `VIRTUAL_ENV` environment variable

### Import Errors
- Ensure `uv sync` completed successfully
- Restart VS Code/IDE to refresh language server
- Use `uv run` prefix for all python commands

---

## Additional Resources

- [MCP Official Documentation](https://docs.claude.com/en/docs/build-with-claude/mcp)
- [Spotify Web API Reference](https://developer.spotify.com/documentation/web-api)
- [LangChain Documentation](https://python.langchain.com/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

---

## Contributing

This is a learning/prototype repository. Feel free to:
- Add new MCP server implementations
- Enhance existing examples with better error handling
- Document additional patterns and use cases
- Create issues for bugs or unclear documentation

---

## License

MIT License - See LICENSE file for details