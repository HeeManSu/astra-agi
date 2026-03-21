# Astra DSL: Nodes & Edges Architecture

## What Is the DSL?

Astra's **DSL (Domain-Specific Language)** represents AI workflows as **directed graphs** — a set of **nodes** (things that happen) connected by **edges** (the order they happen in).

```
User query → LLM generates Python code → Parser converts to AST → Builder lowers to DSL graph
```

The DSL graph is the final, executable representation of a workflow. It's what the runtime actually runs.

---

## The Two Building Blocks

### Nodes = "What happens"

A node is a single step in the workflow. Think of it as a box on a flowchart.

```
┌──────────────────────┐
│  ActionNode          │  ← Calls an external tool (e.g., "get stock price")
│  tool: analyst.fetch │
│  inputs: {symbol: …} │
└──────────────────────┘
```

### Edges = "What happens next"

An edge is an arrow connecting two nodes. It defines the flow — which node runs after which.

```
[ActionNode: fetch] ──edge──→ [RespondNode: respond]
```

> **Key principle:** Edges are the **single source of truth** for flow routing. Nodes only store their own semantic data (like a condition or a tool name), never "where to go next."

---

## Node Types

There are **5 node types** organized into 2 tiers:

### Tier 1 — Core (the basics)

| Node              | Purpose                                    | Key Fields                  | Example                           |
| ----------------- | ------------------------------------------ | --------------------------- | --------------------------------- |
| **ActionNode**    | Calls an external tool (has side effects)  | `tool`, `inputs`, `outputs` | `analyst.get_stock_price('AAPL')` |
| **TransformNode** | Pure data manipulation (no external calls) | `expression`, `assign_to`   | `total = price * quantity`        |
| **RespondNode**   | Returns the final result to the user       | `message`                   | `synthesize_response(result)`     |

These three cover 90% of what you'll see. Every workflow ends with a `RespondNode`.

### Tier 2 — Control Flow (branching and looping)

| Node           | Purpose                     | Key Fields       | Maps to Python       |
| -------------- | --------------------------- | ---------------- | -------------------- |
| **BranchNode** | Routes based on a condition | `condition`      | `if data:`           |
| **LoopNode**   | Iterates over a collection  | `over`, `as_var` | `for item in items:` |

---

## Edge Types and Roles

Every edge has two important properties:

### Edge Type — _how_ the edge works

| Type          | Meaning                         | When Used                  |
| ------------- | ------------------------------- | -------------------------- |
| `SEQUENTIAL`  | "A finishes → B starts"         | Default flow between steps |
| `CONDITIONAL` | "A finishes → if condition → B" | Branch true/false paths    |

### Edge Role — _why_ the edge exists

The role is the semantic tag that explains the edge's purpose. This is what makes edges the single source of truth — instead of storing "where to go" on the node, the edge itself says "I exist because I'm the true-path of this branch."

| Role               | Used By    | Meaning                                             |
| ------------------ | ---------- | --------------------------------------------------- |
| `NONE`             | Any        | Plain sequential flow, no special purpose           |
| `THEN`             | BranchNode | True-path (condition is true)                       |
| `ELSE`             | BranchNode | False-path (explicit else block)                    |
| `ELSE_FALLTHROUGH` | BranchNode | False-path (no else block — skip to next statement) |
| `BODY`             | LoopNode   | Entry into the loop body                            |
| `BACK_EDGE`        | LoopNode   | Body tail → loop node (next iteration)              |

### Cardinality Rules

The validator enforces strict rules on how many edges of each role a node can have:

| Node Type  | Required                         | Optional                           |
| ---------- | -------------------------------- | ---------------------------------- |
| BranchNode | Exactly 1 `THEN`                 | Max 1 `ELSE` or `ELSE_FALLTHROUGH` |
| LoopNode   | Exactly 1 `BODY`, ≥1 `BACK_EDGE` | —                                  |

---

## How It All Fits Together

### From Python code to DSL graph

Here's a real example. This Python code:

```python
data = analyst.fetch_data(symbol='AAPL')
if data:
    report = analyst.analyze(data)
else:
    report = analyst.fallback()
synthesize_response(report)
```

Gets lowered into this graph:

```
                    ┌─────────────────────┐
                    │ ActionNode: "data"   │
                    │ tool: analyst.fetch  │
                    └────────┬────────────┘
                             │  (sequential, role=NONE)
                             ▼
                    ┌─────────────────────┐
              ┌─────│ BranchNode          │─────┐
              │     │ condition: "data"   │     │
              │     └─────────────────────┘     │
              │                                 │
     (conditional,                    (conditional,
      role=THEN)                       role=ELSE)
              │                                 │
              ▼                                 ▼
   ┌──────────────────┐            ┌──────────────────┐
   │ ActionNode        │            │ ActionNode        │
   │ tool: .analyze    │            │ tool: .fallback   │
   └────────┬─────────┘            └────────┬─────────┘
            │  (sequential,                 │  (sequential,
            │   role=NONE)                  │   role=NONE)
            │                               │
            └───────────┬───────────────────┘
                        ▼
               ┌─────────────────┐
               │ RespondNode     │
               │ message: report │
               └─────────────────┘
```

### The actual JSON

The graph above serializes to this JSON (simplified):

```json
{
  "name": "stock_analysis",
  "entry": "n_b309e617",
  "nodes": [
    {
      "type": "action",
      "id": "n_b309e617",
      "label": "data",
      "tool": "analyst.fetch_data",
      "inputs": { "symbol": "'AAPL'" },
      "outputs": { "result": "$.data" }
    },
    {
      "type": "branch",
      "id": "n_bb0f3cb4",
      "label": "branch_1",
      "condition": "data"
    },
    {
      "type": "action",
      "id": "n_1cbdd6f8",
      "label": "report",
      "tool": "analyst.analyze",
      "inputs": { "arg_0": "data" },
      "outputs": { "result": "$.report" }
    },
    {
      "type": "action",
      "id": "n_0a47b7e3",
      "label": "report",
      "tool": "analyst.fallback",
      "outputs": { "result": "$.report" }
    },
    {
      "type": "respond",
      "id": "n_1786d705",
      "label": "respond",
      "message": "report"
    }
  ],
  "edges": [
    {
      "source": "n_b309e617",
      "target": "n_bb0f3cb4",
      "type": "sequential",
      "role": ""
    },
    {
      "source": "n_bb0f3cb4",
      "target": "n_1cbdd6f8",
      "type": "conditional",
      "role": "then",
      "condition": "data"
    },
    {
      "source": "n_bb0f3cb4",
      "target": "n_0a47b7e3",
      "type": "conditional",
      "role": "else",
      "condition": "not (data)"
    },
    {
      "source": "n_1cbdd6f8",
      "target": "n_1786d705",
      "type": "sequential",
      "role": ""
    },
    {
      "source": "n_0a47b7e3",
      "target": "n_1786d705",
      "type": "sequential",
      "role": ""
    }
  ]
}
```

Notice:

- **Nodes** only store their own data (tool name, condition, message)
- **Edges** store all routing (source → target, type, role, condition)
- The BranchNode has **no** `then_node` or `else_node` fields — the edges handle it

---

## For-Loop Example

```python
items = analyst.get_items()
for item in items:
    result = analyst.process(item)
synthesize_response(result)
```

```
┌──────────────────────┐
│ ActionNode: "items"  │
│ tool: .get_items     │
└────────┬─────────────┘
         │  (sequential, role=NONE)
         ▼
┌──────────────────────┐
│ LoopNode             │◄─────────────────┐
│ over: $.items        │                  │
│ as_var: item         │    (sequential,  │
└────────┬─────────────┘     role=BACK_EDGE)
         │                                │
    (sequential,                          │
     role=BODY)                           │
         │                                │
         ▼                                │
┌──────────────────────┐                  │
│ ActionNode: "result" │──────────────────┘
│ tool: .process       │
└──────────────────────┘

Loop exits via sequential edge (role=NONE) to:

┌──────────────────────┐
│ RespondNode          │
│ message: result      │
└──────────────────────┘
```

Key edges:

- **BODY**: LoopNode → first body node (enters the loop)
- **BACK_EDGE**: last body node → LoopNode (iterates again)
- **NONE**: LoopNode → next statement (when iteration completes)

---

## If Without Else (ELSE_FALLTHROUGH)

```python
data = analyst.fetch(symbol='AAPL')
if data:
    report = analyst.analyze(data)
synthesize_response(data)
```

When there's no `else` block, the false-path gets a special role: `ELSE_FALLTHROUGH`. This means "the condition was false, skip the body and go directly to the next statement."

```
┌────────────────┐
│ BranchNode     │
│ condition:data │
└──┬──────────┬──┘
   │          │
 (THEN)    (ELSE_FALLTHROUGH)
   │          │
   ▼          │
┌──────────┐  │
│ analyze  │  │
└──┬───────┘  │
   │          │
   └────┬─────┘
        ▼
┌────────────────┐
│ RespondNode    │
└────────────────┘
```

Why not just use a regular sequential edge? Because `ELSE_FALLTHROUGH` makes the intent **explicit** — anyone reading the graph knows this edge exists because the if-statement had no else block, not because it's just normal sequential flow.

---

## Tool Classification

When the builder encounters `analyst.fetch_data(symbol='AAPL')`, how does it know this is a tool call?

**Answer: the whitelist.** The sandbox extracts known tool names from the **semantic layer** (which describes all available agents and their tools) and passes them to the builder:

```
Semantic Layer → allowed_tools = {"analyst.fetch_data", "analyst.analyze", ...}
```

| Call pattern                 | In whitelist? | Becomes                              |
| ---------------------------- | ------------- | ------------------------------------ |
| `analyst.fetch_data('AAPL')` | ✅ Yes        | **ActionNode** (external tool call)  |
| `helper.local_method(data)`  | ❌ No         | **TransformNode** (pure computation) |
| `str.upper()`                | ❌ No         | **TransformNode**                    |

This prevents local helper methods, string operations, and other non-tool calls from being misclassified as external tool invocations.

---

## File Map

| File                                                                                                                                     | What It Does                                                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [edges.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/edges.py)                   | `PlanEdge` dataclass, `EdgeType` enum, `EdgeRole` enum, factory helpers (`sequential`, `conditional`, `error_edge`), lookup helpers (`by_role`, `outgoing`, `incoming`) |
| [nodes.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/nodes.py)                   | `PlanNode` base + 5 concrete node dataclasses, `NodeType` enum                                                                                                          |
| [schema.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/schema.py)                 | `ExecutionPlan` container (holds all nodes + edges), structural validation, `edge_by_role()` helper                                                                     |
| [plan_builder.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/plan_builder.py)     | AST → DSL lowering. Walks Python AST, creates nodes + edges with roles                                                                                                  |
| [plan_validator.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/plan_validator.py) | Semantic validation: cardinality rules, cycle detection, state binding checks                                                                                           |
| [ast_parser.py](file:///Users/himanshu/Desktop/open-source/Astra/astra/framework/src/framework/code_mode/compiler/ast_parser.py)         | Python code → AST parsing + restricted-subset validation                                                                                                                |

---

## Quick Reference: Reading a DSL JSON

When you see a DSL JSON file, here's how to read it:

1. **Find `entry`** — that's the first node ID
2. **Find that node in `nodes`** — read its `type` and fields
3. **Find edges where `source` = that node ID** — those are the outgoing connections
4. **Read `role`** on each edge — that tells you _why_ the edge exists
5. **Follow `target`** — that's the next node
6. **Repeat** until you hit a `respond` or `terminate` node
