# Benchmarking — five frameworks, one workload

This directory benchmarks five multi-agent frameworks on the same investment-research workload. The point is to compare orchestration **architectures**, not vendors:

| Architecture | Implementation(s) |
| --- | --- |
| Compiler | **Astra** (ours) |
| ReAct (model-in-the-loop) | **Agno**, **CrewAI**, **AutoGen** |
| Hand-authored graph | **LangGraph** |

Same model (`gemini-2.5-flash`, `temperature=0.0`, thinking off), same tools (`yfinance` + FRED), byte-identical agent prompts, same six queries. Only the orchestration framework changes.

---

## Layout

```
benchmarking/
├── run.py                       # orchestrator (one subprocess per trial)
├── harness/                     # shared measurement layer
│   └── harness/
│       ├── __init__.py
│       └── counter.py           # TokenCounter — patches google.genai
├── astra-invesment-team/        # 1 directory per framework — each a self-contained uv project
├── agno-investment-team/        # each contains its own run.py (the single-trial runner)
├── crewai-investment-team/
├── autogen-investment-team/
└── langgraph-investment-team/

runs/                            # output: one folder per (framework, query, trial)
└── <framework>/<query>_trial<N>/
    ├── <framework>.log          # framework's verbose stdout (tee'd while running)
    ├── call_NNN_request.json    # full request payload sent to Gemini
    ├── call_NNN_response.json   # full response from Gemini (incl. usage_metadata)
    ├── summary.json             # per-trial token totals + per-call breakdown
    ├── response.txt             # the framework's final response
    └── result.json              # one-line trial summary (calls, tokens, wall, ok)
```

---

## Running — step by step

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager (`brew install uv` on macOS)
- A **Google Gemini API key** (free at <https://aistudio.google.com/apikey>)
- A **FRED API key** for the macro tools (free at <https://fred.stlouisfed.org>)

No MongoDB or other backend is needed — the benchmark writes everything to local `runs/` folders.

### Step 1 — Set API keys

Put your keys in `Astra/.env` at the repo root (one level up from `benchmarking/`):

```env
GOOGLE_API_KEY=your-google-genai-key
FRED_API_KEY=your-fred-key
```

(`GEMINI_API_KEY` works as an alias. Each framework directory also accepts a local `.env` if you want per-framework overrides.)

### Step 2 — Sync each framework's dependencies (first time only)

Each framework is a self-contained uv project with its own pinned dependencies. Sync them once:

```bash
cd benchmarking
for fw in astra-invesment-team agno-investment-team crewai-investment-team \
          autogen-investment-team langgraph-investment-team; do
  uv sync --project "$fw"
done
```

This creates a `.venv` inside each framework directory. The five venvs are isolated so the frameworks' top-level module names (which sometimes conflict) don't interfere.

### Step 3 — Run one framework

The full matrix per framework is 6 queries × 3 trials = 18 trials. Each takes ~25-90s depending on the framework. From `benchmarking/`:

```bash
# Astra (the compiler — fastest, ~10 min total)
uv run --project astra-invesment-team   python run.py --framework astra

# Agno (ReAct coordinator)
uv run --project agno-investment-team   python run.py --framework agno

# CrewAI (Process.hierarchical)
uv run --project crewai-investment-team python run.py --framework crewai

# AutoGen (SelectorGroupChat)
uv run --project autogen-investment-team python run.py --framework autogen

# LangGraph (hand-authored graph)
uv run --project langgraph-investment-team python run.py --framework langgraph
```

You can run all five back-to-back, or in parallel terminals if your rate limits allow it.

### Step 4 — Inspect the output

Every trial produces a self-contained folder under `runs/<framework>/<query>_trial<N>/`:

```bash
ls benchmarking/runs/astra/Q1_trial0/
# agno.log  call_001_request.json  call_001_response.json  ...
# response.txt  result.json  summary.json
```

The one-line summary is in `result.json`:

```bash
cat benchmarking/runs/astra/Q1_trial0/result.json
# {"framework": "astra", "query_id": "Q1", "ok": true,
#  "num_llm_calls": 3, "total_tokens": 18335, "wall_ms": 25600, ...}
```

See [Inspecting a run in detail](#inspecting-a-run-in-detail) below for what each file contains.

### Step 5 — Subsets, re-runs, and single trials

**Run a single query for fewer trials:**

```bash
uv run --project agno-investment-team python run.py \
    --framework agno --queries Q7 --trials 1
```

**Force a re-run** of trials that already completed (otherwise they're skipped):

```bash
uv run --project agno-investment-team python run.py --framework agno --force
```

**Run a single trial directly** (no orchestrator, useful for debugging):

```bash
cd agno-investment-team
uv run python run.py --query Q7 --trial 0
```

**Dry-run** to preview what would be executed:

```bash
uv run --project agno-investment-team python run.py --framework agno --dry-run
```

---

## How tokens are counted

The number we report is **what Google's API actually billed for**, not a tokenizer estimate.

Every framework, regardless of its internal abstractions, eventually calls Google's `google.genai` SDK to talk to Gemini. We measure at that exact boundary:

1. **Class-level patch.** Before each trial, `TokenCounter` (in [`harness/harness/counter.py`](harness/harness/counter.py)) monkey-patches the four entry points on the SDK's `Models` / `AsyncModels` classes: `generate_content`, `generate_content_stream`, and their async siblings. The patch wraps each call; it doesn't change inputs or behavior.
2. **Every call captured.** On each wrapped call, the counter:
   - serializes the full request payload to `call_NNN_request.json`,
   - serializes the full response (including `usage_metadata`) to `call_NNN_response.json`,
   - reads `usage_metadata.prompt_token_count`, `candidates_token_count`, and `thoughts_token_count` directly from Google's response,
   - records the call in `summary.json` along with model id, latency, tool calls emitted, and a short text preview.
3. **Per-trial totals** are summed from the per-call usage_metadata. `result.json` reports `prompt_tokens`, `completion_tokens`, `thoughts_tokens`, `total_tokens`, `num_llm_calls`, `wall_ms`, and `llm_latency_ms`.

Two consequences worth knowing:

- **Source of truth is Google.** If a framework's own counter disagrees with `result.json`, the framework's counter is wrong — the bytes in `call_NNN_response.json` come directly off the wire.
- **Independently verifiable.** Anyone who wants to double-check can re-tokenize the captured `call_NNN_request.json` payloads with `google.genai.Client.models.count_tokens()` and confirm the numbers match `usage_metadata`. We have done this; the SDK's reported counts and a fresh `count_tokens` recount agree to single tokens.

---

## Inspecting a run in detail

Every trial leaves a self-contained folder under `runs/<framework>/<query>_trial<N>/`. To inspect what a framework actually did on a given trial, open that folder:

| File | What's in it |
|------|--------------|
| `<framework>.log` | The framework's own verbose stdout — every prompt, tool call, tool result, and model response, in order. |
| `call_NNN_request.json` | The full request payload sent to Gemini on call N. `contents` is the message history, `tools` is the function schema, `system_instruction` is the framework's system prompt. |
| `call_NNN_response.json` | The full response. Includes `candidates[0].content` (the text / tool calls), `usage_metadata` (the official token counts), and `finish_reason`. |
| `summary.json` | Per-trial token totals plus a per-call breakdown (tokens, model id, latency, tool calls emitted). |
| `response.txt` | The final stitched response that the framework returned to the user. |
| `result.json` | One-line summary: framework, query, trial, ok flag, attempts used, all token counts, wall time, response length. |

So the answer to "how many tokens did Agno actually use on Q7/trial2?" is in `runs/agno/Q7_trial2/result.json`. And the answer to "show me every single API call it made" is the sorted `call_NNN_*.json` files in the same folder.

---

## How fairness is enforced

The frameworks differ a lot in their public APIs, so parity has to be enforced explicitly:

- **Model.** Every framework constructs the same Gemini client (`gemini-2.5-flash`, `temperature=0.0`, thinking tokens disabled). See each `agents/settings.py`.
- **Tools.** The 17 tools (yfinance + FRED calls for the 4 analysts) are the same Python implementations across frameworks. Only the binding wrapper differs (Astra's `@bind_tool`, Agno's plain functions, CrewAI's `@tool`, AutoGen's `FunctionTool`, LangGraph's `@tool`).
- **Prompts.** The instruction text for each analyst is byte-identical across frameworks. AutoGen adds a small `TEAM_CONTEXT` footer; see the note below.
- **Queries.** All `run.py` files use the same six-query dictionary (Q1, Q2, Q3, Q6, Q7, Q9).
- **Token counting.** Every framework routes through `google.genai`; `TokenCounter` patches the SDK at the class level (see [How tokens are counted](#how-tokens-are-counted)).
- **Orchestration mode.** Every ReAct framework runs in its **leader-driven** mode (Agno's coordinator, CrewAI's `Process.hierarchical` with `manager_llm`, AutoGen's `SelectorGroupChat`).

### One disclosed prompt difference: AutoGen's `TEAM_CONTEXT` footer

AutoGen's analyst prompts have a small added footer (see [`autogen-investment-team/agents/settings.py`](autogen-investment-team/agents/settings.py)). It tells each specialist to produce its section even on compound queries (e.g., "compare AAPL and MSFT").

This is needed because AutoGen's `SelectorGroupChat` passes the raw user query through to each selected speaker. The other frameworks have a manager that **reframes** the user query into per-analyst sub-tasks before delegating, so each analyst only sees a scoped task. Without the footer, AutoGen's analysts refuse compound queries because their prompts say "do not make allocation decisions" and the raw query asks for exactly that.

This is the only prompt difference. It is disclosed in the paper's §4.4 and in the AutoGen agents' module docstrings.

---

## Reproducibility notes

- Each trial runs in a fresh subprocess; no in-memory state carries between trials.
- A 2-second sleep between trials reduces Gemini API rate-limit collisions.
- Each framework's `run.py` retries up to 3 times if the response comes back empty (some transient Gemini errors are silently swallowed by frameworks).
- Every per-trial output (request, response, summary, log, final response) is written under `runs/<framework>/<query>_trial<N>/`. Token totals in `result.json` are summed from the SDK's own `usage_metadata`, and can be independently recomputed from the captured request files using `google.genai`'s `count_tokens()`.

---

## Adding a new framework

1. Copy one of the existing framework directories as a template.
2. Implement the same 4 analysts with byte-identical prompt text and the same tool list.
3. Configure your framework's LLM client to use `gemini-2.5-flash`, `temperature=0.0`, thinking disabled.
4. Make sure every model call routes through `google.genai` so `TokenCounter` catches it. If your framework ships its own Gemini client, see [`autogen-investment-team/agents/gemini_client.py`](autogen-investment-team/agents/gemini_client.py) for an example of wiring a custom client through `google.genai`.
5. Add a `run.py` in the new framework directory (copy any existing one and adjust the framework-specific bits).
6. Add an entry to `SIDE_DIR` in the top-level `run.py`.

That's the whole contract: same model, same tools, same prompts, same queries, route through `google.genai`. Everything else is the framework's business.
