# Test Server for Playground API Testing

This is a comprehensive test server setup for testing and debugging the Astra Playground API endpoints, especially the `/api/playground/agents` endpoint.

## Quick Start

### Method 1: Using VS Code Debugger (Recommended)

1. Open VS Code
2. Go to Run and Debug (F5 or Cmd+Shift+D)
3. Select "Python: Test Server - Playground API"
4. Click the play button or press F5
5. The server will start on `http://127.0.0.1:8000`

### Method 2: Command Line

```bash
cd packages/runtime
python examples/test_server/main.py
```

### Method 3: Using uvicorn directly

```bash
cd packages/runtime
uvicorn examples.test_server.main:app --reload --host 127.0.0.1 --port 8000
```

## Accessing the API

Once the server is running:

1. **OpenAPI Documentation (Interactive)**: http://127.0.0.1:8000/docs

   - Interactive API documentation with "Try it out" functionality
   - Test endpoints directly from the browser
   - See request/response schemas

2. **ReDoc Documentation**: http://127.0.0.1:8000/redoc

   - Alternative documentation format

3. **Playground Agents Endpoint**: http://127.0.0.1:8000/api/playground/agents

   - Direct GET request to test the endpoint
   - Returns list of all agents with their details

4. **Playground UI**: http://127.0.0.1:8000/
   - Full playground interface (if built)

## Testing the Playground Agents API

### Using OpenAPI Docs (Easiest)

1. Start the server
2. Go to http://127.0.0.1:8000/docs
3. Find the `/api/playground/agents` endpoint under "Playground - Agents"
4. Click "Try it out"
5. Click "Execute"
6. See the response with all agent details

### Using curl

```bash
curl http://127.0.0.1:8000/api/playground/agents
```

### Using Python requests

```python
import requests

response = requests.get("http://127.0.0.1:8000/api/playground/agents")
print(response.json())
```

## Debugging

### Setting Breakpoints

1. Open `packages/runtime/src/astra/server/routes/playground/agents.py`
2. Set a breakpoint on line 33 (inside `list_agents` function)
3. Start the debugger
4. Make a request to `/api/playground/agents`
5. The debugger will pause at your breakpoint

### Debugging Tips

- **Breakpoint in route handler**: Set breakpoint in `list_agents()` function
- **Breakpoint in agent creation**: Set breakpoint in `create_test_agents()` function
- **Watch variables**: Use VS Code's watch panel to monitor `registry.agents`, `agent.model`, etc.
- **Step through code**: Use F10 (step over), F11 (step into), Shift+F11 (step out)

## Configuration

The test server creates multiple agents with different configurations:

- **Simple Agent**: Basic agent with no tools
- **Agent with Tools**: Agent with multiple tools
- **Agent with Storage**: Agent with MongoDB storage
- **Agent with Model**: Agent with specific model configuration

You can modify `create_test_agents()` in `main.py` to add more test agents.

## Environment Variables

The test server reads environment variables from:

1. `.env` file in `packages/runtime/` directory (recommended)
2. System environment variables (fallback)

### Required Variables

- `ASTRA_JWT_SECRET`: JWT secret for authentication (defaults to "dev-secret-for-testing")
- `MONGODB_URL`: MongoDB connection URL (defaults to "mongodb://localhost:27017")

### Optional Variables

- `HOST`: Server host (defaults to "127.0.0.1")
- `PORT`: Server port (defaults to 8000)

### Setting Up .env File

1. Create a `.env` file in `packages/runtime/` directory:

```bash
cd packages/runtime
touch .env
```

2. Add your environment variables:

```bash
# .env file in packages/runtime/
ASTRA_JWT_SECRET=your-secret-key-here
MONGODB_URL=mongodb://localhost:27017
```

**Note**: The `.env` file should be placed in `packages/runtime/` (the parent directory of `examples/test_server/`), not inside `test_server/` folder. This is because the script runs from `packages/runtime/` directory.

## Troubleshooting

### Server won't start

- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check Python path is set correctly

### Agents not showing up

- Verify agents are created successfully (check logs)
- Check registry is populated (set breakpoint in `create_app`)
- Verify agent IDs are set correctly

### Debugger not hitting breakpoints

- Ensure `justMyCode: false` in launch.json
- Check that you're using the correct Python interpreter
- Verify the file path matches the breakpoint location
