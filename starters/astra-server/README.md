# Astra Server Template

This is a production-ready template for building AI agents with [Astra](https://github.com/HeeManSu/astra-agi).

## Features

- 🚀 **Production Server**: Built on FastAPI and Astra Runtime.
- 🧩 **Modular Agents**: Easy to add and configure new agents.
- ⚡ **High Performance**: Async-first architecture.
- 🐳 **Docker Ready**: Optimized Dockerfile included.

## Quick Start

1. **Install uv** (recommended package manager):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Set up environment**:

   ```bash
   cp .env.example .env
   # Edit .env and add your API keys (e.g., OPENAI_API_KEY, GEMINI_API_KEY)
   ```

4. **Run the server**:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

   Open [http://localhost:8000/docs](http://localhost:8000/docs) to see the API Swagger UI.

## Adding Agents

1. Create a new file in `app/agents/` (e.g., `my_agent.py`).
2. Define your agent using the `@agent` decorator or `Agent` class.
3. Register it in `app/main.py`.

## Deployment

### Docker

Build and run with Docker:

```bash
docker build -t astra-app .
docker run -p 8000:8000 -d astra-app
```
