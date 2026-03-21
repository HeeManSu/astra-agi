# astra-framework

**The execution engine for compiler-based multi-agent AI.** Instead of ReAct loops where the LLM decides each step at runtime, Astra compiles the entire execution plan upfront — one LLM call, deterministic output.

```
LLM call → restricted Python → AST validation → ExecutionGraph → deterministic run
```

---

## Why Not ReAct?

| | ReAct / Tool-calling | Astra |
|---|---|---|
| LLM calls per task | Unbounded (N loops) | **Fixed — 1 planning call** |
| Execution path | Decided at runtime | **Compiled upfront** |
| Tool call order | Non-deterministic | **Guaranteed** |
| Debuggability | Hard — emergent behavior | **Inspect the graph before running** |
| Token cost | Grows with task complexity | **Constant** |

---

## Installation

```bash
pip install astra-framework
```

**Optional extras:**

```bash
pip install astra-framework[aws]      # AWS Bedrock (Claude, etc.)
pip install astra-framework[mongodb]  # MongoDB storage backend
pip install astra-framework[all]      # Everything
```

**Requires:** Python 3.10+

---

## Quick Start

```python
from framework import Agent, Sandbox, build_entity_semantic_layer, generate_stubs
from framework.models import Gemini

# 1. Define your agents with tools
market_analyst = Agent(
    name="market_analyst",
    model=Gemini("gemini-2.0-flash"),
    instructions="Analyse stock fundamentals and price trends.",
    tools=[get_stock_price, get_financials],
)

risk_officer = Agent(
    name="risk_officer",
    model=Gemini("gemini-2.0-flash"),
    instructions="Evaluate investment risk.",
    tools=[calculate_risk_score],
)

# 2. Build the semantic layer — describes your team to the compiler
semantic_layer = build_entity_semantic_layer(
    agents=[market_analyst, risk_officer],
    task="Analyse AAPL and assess investment risk",
)

# 3. Generate stubs — typed Python signatures the LLM can reason over
stubs = generate_stubs(semantic_layer)

# 4. Run the compiler — one LLM call produces the entire execution plan
sandbox = Sandbox(agents=[market_analyst, risk_officer])
result = await sandbox.execute(semantic_layer=semantic_layer, stubs=stubs)

print(result.output)   # Final answer
print(result.plan)     # The compiled ExecutionGraph — inspect it
```

---

## Core Concepts

### Semantic Layer

The semantic layer translates your agents and their tools into a typed schema the compiler can reason over. It captures:
- What each agent does (instructions)
- What tools it has (name, parameters, return type)
- What the overall task is

```python
from framework import build_entity_semantic_layer

semantic_layer = build_entity_semantic_layer(
    agents=[analyst, risk_officer, memo_writer],
    task="Full investment analysis for AAPL",
)
```

### Compiler

The compiler takes the semantic layer and produces a restricted Python program, then validates it against an AST whitelist before lowering it to an `ExecutionGraph`. Only a safe subset of Python is allowed — no imports, no file I/O, no network calls — just tool calls and data flow.

```
semantic_layer
    → LLM generates restricted Python
    → AST parser validates (banned nodes, nesting limits, tool whitelist)
    → plan_builder lowers to ExecutionGraph
    → plan_validator checks graph structure
```

### Sandbox

The `Sandbox` executes the validated `ExecutionGraph` deterministically. Each node in the graph maps to a tool call on a specific agent. The executor dispatches calls in order, passes results between nodes, and collects the final output.

```python
result = await sandbox.execute(semantic_layer=semantic_layer, stubs=stubs)

result.output        # str — the final answer
result.plan          # ExecutionGraph — the compiled plan
result.tool_calls    # list — every tool call made, in order
result.duration_ms   # int — total wall-clock time
```

### MCP Support

Agents can use tools from any MCP (Model Context Protocol) server:

```python
from framework.tool.mcp import MCPToolkit

exa_toolkit = MCPToolkit(
    name="exa",
    slug="exa-search",
    command="npx",
    args=["-y", "exa-mcp-server"],
)

analyst = Agent(
    name="analyst",
    tools=[exa_toolkit],
    ...
)
```

---

## API Reference

### `build_entity_semantic_layer(agents, task)`

Builds a typed `EntitySemanticLayer` from a list of `Agent` instances and a task string.

### `build_domain_schema(semantic_layer)`

Converts an `EntitySemanticLayer` into a `DomainSchema` — the structured representation used by the compiler.

### `generate_stubs(semantic_layer)`

Generates Python stub code from the semantic layer. The stubs give the LLM typed function signatures to write against during the planning call.

### `Sandbox(agents)`

The execution engine. Call `.execute(semantic_layer, stubs)` to run the full compiler pipeline and return a `SandboxResult`.

### `SandboxResult`

| Field | Type | Description |
|---|---|---|
| `output` | `str` | Final answer |
| `plan` | `ExecutionGraph` | The compiled plan |
| `tool_calls` | `list[ToolCall]` | Every call made, in order |
| `duration_ms` | `int` | Total execution time |
| `error` | `str \| None` | Error message if execution failed |

### `Agent(name, model, instructions, tools, memory)`

An agent with a model, instructions, and tools. Agents are passive — the `Sandbox` drives their execution according to the compiled plan.

### `Memory(num_history_turns)`

Conversation memory. Plugs into `Agent` to include recent history in context.

---

## Model Support

| Provider | Import |
|---|---|
| Google Gemini | `from framework.models import Gemini` |
| OpenAI GPT | `from framework.models import OpenAI` |
| AWS Bedrock | `from framework.models.aws import Bedrock` |

---

## Related Packages

| Package | Role |
|---|---|
| [`astra-runtime`](../runtime) | FastAPI server that hosts your agents over HTTP |
| [`astra-observability`](../observability) | Tracing, spans, and telemetry |

---

## License

[MIT](LICENSE) — Copyright © 2025 Himanshu Sharma
