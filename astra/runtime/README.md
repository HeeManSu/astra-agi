# Astra Runtime

Embedded server for running AI agents.

## Installation

```bash
pip install astra-runtime
```

## Quick Start

```python
from runtime import AstraServer
from framework import Agent

# Create your agent
my_agent = Agent(
    name="assistant",
    model=...,
    system_prompt="You are a helpful assistant.",
)

# Create server
server = AstraServer(
    agents=[my_agent],
)

# Get FastAPI app
app = server.get_app()
```

Then run with:

```bash
uvicorn main:app --reload
```

## API Endpoints

| Endpoint                 | Method | Description           |
| ------------------------ | ------ | --------------------- |
| `/health`                | GET    | Health check          |
| `/agents`                | GET    | List agents           |
| `/agents/{id}`           | GET    | Get agent             |
| `/agents/{id}/run`       | POST   | Run agent             |
| `/teams`                 | GET    | List teams            |
| `/teams/{id}/run`        | POST   | Run team              |
| `/threads`               | POST   | Create thread         |
| `/threads/{id}/messages` | GET    | Get messages          |
| `/chat/stream`           | POST   | Stream response (SSE) |
