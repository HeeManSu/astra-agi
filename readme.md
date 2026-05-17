# Astra

> [!WARNING]
> **🚧 This project is under active development and has not been released yet.** APIs, architecture, and documentation may change significantly. Contributions and feedback are welcome, but please expect breaking changes.

**A code-first DSL compiler for multi-agent orchestration.**

Most agent frameworks run the language model inside a ReAct loop at every step. Astra runs it three times: once to plan, once to generate a short Python program, and once to synthesize the final response. In between, a deterministic executor runs the compiled graph with zero model calls. The number of LLM calls is fixed at three per query, regardless of how many tools the workflow involves.

```
LLM call → restricted Python → AST validation → typed graph → deterministic execution
```

---

## Headline numbers

On a 4-analyst investment-research workload (90 trials, 5 frameworks):

| Architecture            | n  | LLM calls | tokens (mean / p95)     | wall p50 (s) |
| ----------------------- | -- | --------- | ----------------------- | ------------ |
| **Compiler (Astra)**    | 18 | **3.0**   | **21,013 / 28,804**     | **26.1**     |
| ReAct pool (Agno+CrewAI+AutoGen) | 54 | 16.1 | 49,219 / 85,452 | 50.3 |
| Hand-graph (LangGraph)  | 18 | 10.4      | 29,645 / 55,086         | 32.4         |

Against the pooled ReAct baseline: **5.37× fewer LLM calls, 2.34× fewer tokens, 1.93× faster wall p50**. Tail gap on tokens is 2.97× (p95).

Full numbers, ratios, per-query breakdown, and reproduction instructions: [`benchmarking/`](benchmarking/) and [`docs/research.md`](docs/research.md). Paper PDF: [`paper/main.pdf`](paper/main.pdf).

---

## Repository layout

```
Astra/
├── astra/                  the framework, runtime, and observability packages
│   ├── framework/             astra-framework — compiler + execution engine
│   ├── runtime/               astra-runtime — embeddable FastAPI server
│   ├── observability/         astra-observability — telemetry capture
│   └── README.md              package docs + local-run guide
│
├── benchmarking/           five-framework comparison harness
│   ├── run.py                 orchestrator (subprocess-per-trial)
│   ├── harness/               TokenCounter (patches google.genai)
│   ├── astra-invesment-team/  Astra's investment team
│   ├── agno-investment-team/  Agno's investment team
│   ├── crewai-investment-team/
│   ├── autogen-investment-team/
│   ├── langgraph-investment-team/
│   ├── runs/                  per-trial outputs (logs, request/response JSON, summary)
│   └── README.md              benchmark workflow + token-counting details
│
├── docs/
│   └── research.md            full research write-up (markdown source of the paper)
│
├── paper/
│   ├── main.tex               LaTeX source
│   ├── main.pdf               compiled paper
│   └── references.bib
│
├── astra-playground-ui/    Next.js dev UI for running Astra locally
└── cookbook/               example agent teams
```

---

## Quick start

The fastest path to a working setup is the investment-team example, which spins up a 7-agent investment committee with a Playground UI.

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/), MongoDB, Node.js + yarn (for the UI).

```bash
# 1. Install runtime + example deps
cd astra/runtime
uv sync

# 2. Configure your model key in repo root .env
echo "GOOGLE_API_KEY=your-key" > ../../.env

# 3. Start the backend
uv run uvicorn examples.investment_team.main:app --host 127.0.0.1 --port 8000

# 4. (Optional) Start the Playground UI in a second terminal
cd ../../astra-playground-ui && yarn install && yarn dev
```

Full instructions, env-var reference, and a one-click VS Code debug config (compound launch — backend + frontend together) are in [`astra/README.md`](astra/README.md).

---

## Why compile, not loop?

|                              | ReAct / tool-calling          | Astra                                       |
| ---------------------------- | ----------------------------- | ------------------------------------------- |
| LLM calls per query          | Unbounded (one per tool step) | **Fixed — 3 calls**                         |
| Execution path               | Decided at runtime            | **Compiled upfront**                        |
| Tool-call order              | Non-deterministic             | **Guaranteed by the typed graph**           |
| Inspectability               | Emergent after the fact       | **Full plan visible before any tool runs**  |
| Safety                       | Runtime, ad-hoc               | **Compile-time AST validation**             |
| Token cost on heavy queries  | Grows with workload           | **Bounded by plan size**                    |

The trade-off: Astra doesn't replan mid-execution. For workflows where the next step legitimately depends on what an earlier tool returned, a ReAct loop adapts and Astra doesn't (yet). For sequential, structured pipelines — which most multi-agent workflows are — the compile-time approach wins on every cost axis we measure.

---

## What's in the box

- **Compiled execution graph.** The LLM produces a Python plan once. A typed graph is compiled from the AST and executed by a deterministic cursor-based runner with zero model calls during execution.
- **Bounded LLM calls.** Three calls per query, every query — planner, code-gen, response synthesis. Cost is a fixed compile-time bill, not a per-step bill.
- **Compile-time safety.** AST-level validator rejects `import`, `exec`, `eval`, `open`, attribute introspection, and arbitrary control flow. Generated code cannot reach the shell, the file system, or any tool that wasn't registered.
- **Typed execution graph.** Five node types (action, transform, respond, branch, loop) connected by semantic edges.
- **Replayable journal.** Every node visit recorded with inputs, outputs, duration, and errors. Re-run any trace offline for debugging or audit.
- **Multi-agent teams.** Compose `Agent` objects into `Team` objects, and teams into pipelines.
- **MCP support.** Register tools from any Model Context Protocol server (Exa, Brave Search, custom toolkits) alongside native Python tools.
- **Multi-provider models.** Google Gemini and AWS Bedrock (Claude) supported out of the box.
- **Persistent storage and memory.** MongoDB and libsql/SQLite backends, with a conversational memory layer.
- **Embeddable server.** `AstraServer.get_app()` returns a fully-wired FastAPI app with REST + Server-Sent-Events endpoints.

Full feature breakdown and architecture details: [`astra/README.md`](astra/README.md).

---

## Documentation

| Topic | Location |
| --- | --- |
| Local dev setup | [`astra/README.md`](astra/README.md) |
| Framework API | [`astra/framework/README.md`](astra/framework/README.md) |
| Server runtime | [`astra/runtime/README.md`](astra/runtime/README.md) |
| Observability | [`astra/observability/README.md`](astra/observability/README.md) |
| Benchmark workflow | [`benchmarking/README.md`](benchmarking/README.md) |
| Research write-up | [`docs/research.md`](docs/research.md) |
| Paper PDF | [`paper/main.pdf`](paper/main.pdf) |

---

## Contributing

This project is under active development. If something doesn't work, open an issue. If you want to extend the compiler (new node types, more AST coverage, additional model providers), see the contribution notes in [`astra/framework/README.md`](astra/framework/README.md).

## License

Apache 2.0 — see [`astra/framework/LICENSE`](astra/framework/LICENSE).
