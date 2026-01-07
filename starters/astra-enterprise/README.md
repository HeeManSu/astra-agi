# Astra Enterprise Template

Production-ready enterprise template for building scalable AI agent systems with Astra.

## Structure

```
├── src/
│   └── app/
│       ├── agents/        # Agent definitions
│       ├── api/           # Custom API routes
│       ├── core/          # Core config & settings
│       ├── tools/         # Shared tools library
│       └── main.py        # Entry point
├── tests/                 # Test suite
├── scripts/               # Utility scripts (db migrations etc)
├── docker/                # Docker config
├── .env.example
└── pyproject.toml
```

## Features

- 🏢 **Enterprise Structure**: clear separation of concerns
- 🗄️ **Database Ready**: SQLAlchemy + AsyncPG setup
- 🧪 **Testing**: Pytest setup included
- 🐳 **Docker**: Optimized multi-stage builds

## Quick Start

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Run server**:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
