# Astra

> [!WARNING]
> **🚧 This project is under active development and has not been released yet.** APIs, architecture, and documentation may change significantly. Contributions and feedback are welcome, but please expect breaking changes.

A code-first DSL compiler for multi-agent orchestration. Instead of running a language model inside a ReAct loop at every step, Astra uses the model **once** to produce a short Python program, validates it against compile-time safety rules, compiles it into a typed execution graph, and runs that graph deterministically with no further model calls during execution.

The result: **bounded LLM calls (~3 per query) regardless of how many tools or agents the workflow uses**, plus an inspectable execution plan and a fully replayable audit trail.

---

## Why Astra?

|                              | ReAct / Tool-calling          | Astra                                       |
| ---------------------------- | ----------------------------- | ------------------------------------------- |
| LLM calls per query          | Unbounded (one per tool step) | **Fixed — 3 calls (planner, code-gen, synthesize)** |
| Execution path               | Decided at runtime            | **Compiled upfront**                        |
| Tool call order              | Non-deterministic             | **Guaranteed by the typed graph**           |
| Inspectability               | Emergent after the fact       | **Full plan visible before any tool runs**  |
| Safety                       | Runtime, ad-hoc               | **Compile-time AST validation**             |
| Token cost on heavy queries  | Grows with workload           | **Bounded by plan size**                    |

In our benchmark against Agno, CrewAI, AutoGen, and LangGraph on a 4-analyst investment workload: **5.27× fewer LLM calls, 2.28× fewer tokens, 1.93× faster wall p50** vs the pooled ReAct baseline. Full numbers and reproduction in [`benchmarking/`](../benchmarking/) and [`docs/research.md`](../docs/research.md).

---

## Layout

The `astra/` directory is three independently-installable Python packages plus a runnable example:

```
astra/
├── framework/         astra-framework — the compiler and execution engine
│   └── src/framework/
│       ├── code_mode/     compiler pipeline (AST parser, plan builder, validator, executor)
│       ├── agents/        Agent abstraction with tools, memory, middleware
│       ├── team/          Team coordination (multi-agent groups)
│       ├── tool/          tool decorator, MCP support, semantic-layer builder
│       ├── models/        model providers (Google Gemini, AWS Bedrock)
│       ├── memory/        conversational memory
│       ├── storage/       persistence (MongoDB, libsql/SQLite)
│       ├── middleware/    pre/post hooks on agent calls
│       └── rag/           retrieval-augmented generation
│
├── runtime/           astra-runtime — embeddable FastAPI server
│   └── src/runtime/       AstraServer (REST + streaming endpoints)
│   └── examples/
│       └── investment_team/   reference 7-agent investment committee
│
└── observability/     astra-observability — telemetry capture for runs
    └── src/observability/    storage adapters, trace recording, debug snapshots
```

Each sub-package has its own README with package-level details:

- [`framework/README.md`](framework/README.md) — compiler API and quick-start in Python.
- [`runtime/README.md`](runtime/README.md) — how to embed AstraServer in your app.
- [`observability/README.md`](observability/README.md) — telemetry hooks.

---

## What's in the box

- **Compiled execution graph.** The LLM produces a Python plan once. A typed graph is compiled from the AST and executed by a deterministic cursor-based runner with zero model calls during execution.
- **Bounded LLM calls.** Every query uses the same three calls — planner, code-gen, response synthesis — no matter how many tools the workflow involves. Cost is a fixed compile-time bill, not a per-step bill.
- **Compile-time safety.** AST-level validator rejects `import`, `exec`, `eval`, `open`, attribute introspection, and arbitrary control flow. Generated code cannot reach the shell, the file system, or any tool that wasn't registered.
- **Restricted Python DSL.** Assignments, `if/else`, `for` loops, and a whitelist of safe builtins. Banned: `def`, `class`, `lambda`, `try/except`, `while`, async, comprehensions.
- **Typed execution graph.** Five node types (action, transform, respond, branch, loop) connected by semantic edges. Plan validator enforces unique terminals, reachability, and well-formed branch/loop edges.
- **Replayable execution journal.** Every node visit recorded with inputs, outputs, duration, and errors. Re-run a trace offline for debugging or audit.
- **Multi-agent teams.** Compose `Agent` objects into `Team` objects that compose into pipelines. Each agent has its own tools, memory, and middleware.
- **MCP support.** Register tools from any Model Context Protocol server (Exa, Brave Search, custom toolkits). MCP tools merge into the same semantic layer as native Python tools.
- **Multi-provider models.** Google Gemini (1.5 / 2.0 / 2.5) and AWS Bedrock (Claude family) out of the box. Pluggable for other providers.
- **Persistent storage.** MongoDB and libsql/SQLite backends. Conversational memory layer with configurable history depth.
- **Embeddable FastAPI server.** `AstraServer.get_app()` returns a fully-configured FastAPI app with REST + Server-Sent-Events endpoints, CORS, auth scaffolding, telemetry, and storage wiring.
- **Built-in observability.** Per-call timings, tokens, and errors. Debug snapshots of compiled plans and execution journals. Replayable traces for post-hoc analysis.

---

## Running Locally

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **MongoDB** running locally on `localhost:27017` (needed for the example's storage + telemetry)
- **Node.js + yarn** — only if you want the Playground UI

```bash
# macOS
brew install uv mongodb-community node yarn
brew services start mongodb-community

# Linux: see https://docs.astral.sh/uv/getting-started/installation/
#        and your distro's MongoDB instructions
```

### Install dependencies

The investment-team example has its own deps (`yfinance`, `fredapi`, etc.) declared in `astra/runtime/pyproject.toml`. Sync them into a project-local venv:

```bash
cd astra/runtime
uv sync
```

This is required before the first run. The VS Code debug config uses the same uv-managed env.

### Configure environment

Set your model API key in `Astra/.env` (repo root):

```env
GOOGLE_API_KEY=your-google-genai-key
# Optional, for the investment_team example's macro tools:
FRED_API_KEY=your-fred-api-key
```

The investment-team example also expects:

| Env var             | Value                              | Used for                       |
| ------------------- | ---------------------------------- | ------------------------------ |
| `ASTRA_JWT_SECRET`  | any string (e.g. `dev-secret`)     | JWT signing in `AstraServer`   |
| `MONGODB_URL`       | `mongodb://localhost:27017`        | storage + telemetry            |
| `HOST` / `PORT`     | `127.0.0.1` / `8000`               | bind address                   |

### Run the investment-team example (CLI)

The reference example is a 7-agent investment committee. From the repo root:

```bash
cd astra/runtime
PYTHONPATH="../framework/src:../runtime/src:../observability/src:." \
HOST=127.0.0.1 PORT=8000 \
ASTRA_JWT_SECRET=dev-secret \
MONGODB_URL=mongodb://localhost:27017 \
uv run uvicorn examples.investment_team.main:app \
    --host 127.0.0.1 --port 8000 --reload --reload-exclude '.debug/*'
```

The server will be at `http://127.0.0.1:8000`. Sanity-check with `curl http://127.0.0.1:8000/docs`.

The `PYTHONPATH` line includes the three local packages (`framework`, `runtime`, `observability`) so the example resolves them as source rather than installed wheels. The VS Code debug config sets the same paths for you (next section).

### Run the Playground UI (optional)

In a second terminal, from the repo root:

```bash
cd astra-playground-ui
yarn install   # first time only
yarn dev
```

The UI will start on `http://localhost:3010` and connect to the backend at `127.0.0.1:8000`.

---

## Running in VS Code (debugger)

[`.vscode/launch.json`](../.vscode/launch.json) ships with two debug configurations and a compound that starts both at once. Open the workspace in VS Code and use the **Run and Debug** panel (⌘⇧D / Ctrl+Shift+D):

| Configuration                          | What it runs                                                                                                                                                       |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Backend: Investment Team Server**    | Launches `uvicorn examples.investment_team.main:app` under `debugpy` from `astra/runtime/`. Sets `PYTHONPATH`, `ASTRA_JWT_SECRET`, `MONGODB_URL` for you. Auto-opens `http://127.0.0.1:8000`. Set breakpoints anywhere in the compiler, executor, agents, or tools. |
| **Frontend: Playground Dev Server**    | Runs `yarn run dev` in `astra-playground-ui/`. Auto-opens the dev URL once Vite reports `Local: http://localhost:...`.                                              |
| **Investment Team: Server + Frontend** | Compound that launches both above together. Stopping one stops the other (`stopAll: true`).                                                                        |

The compound is the easiest way to develop end-to-end: pick **Investment Team: Server + Frontend** and hit F5.

> **Tip:** The backend config sets `justMyCode: false`, so you can step into framework code (compiler, validator, executor) directly during a request.

---

## License

Apache 2.0 — see [`framework/LICENSE`](framework/LICENSE).
