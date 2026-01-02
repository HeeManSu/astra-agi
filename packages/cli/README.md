# Astra CLI

CLI for scaffolding and managing Astra server projects.

## Installation

```bash
pip install astra-cli
```

## Commands

| Command                  | Description                 |
| ------------------------ | --------------------------- |
| `astra init server`      | Scaffold new server project |
| `astra add <feature>`    | Add feature to project      |
| `astra remove <feature>` | Remove feature from project |
| `astra dev`              | Run development server      |

## Quick Start

```bash
# Create a new server
astra init server

# Navigate to project
cd my-astra-server

# Install dependencies
pip install -e .

# Run development server
astra dev
```

## Features

Add features to your project:

```bash
astra add rate-limit
astra add observability-otel
astra add ui
```

## License

MIT
