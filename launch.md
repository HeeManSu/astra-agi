# Astra — 4-Day Launch Plan

## Current state (inventory)

### Built (technical core)

| Component | Location | Notes |
|-----------|----------|--------|
| Compiler (AST → plan) | `astra/framework/src/framework/code_mode/compiler/` | `ast_parser.py`, `plan_builder.py`, `plan_validator.py`, `nodes.py`, `edges.py`, `schema.py` |
| Deterministic executor | `astra/framework/src/framework/code_mode/executor/` | `runner.py`, `dispatcher.py` |
| Code mode | `astra/framework/src/framework/code_mode/` | `semantic.py`, `sandbox.py`, `stub_generator.py`, `prompts.py` |
| Investment demo (Astra) | `astra/runtime/examples/investment_team/` | Full example (not under `projects/investment-team/`) |
| Baselines for comparison | `cookbook/agno-investment-team/`, `cookbook/crewai-investment-team/`, `cookbook/langgraph-investment-team/` | Use for Agno / CrewAI benchmarks |

### Done (repo hygiene)

- `astra/framework/src/framework/__init__.py` — narrow public exports (`Agent`, `Astra`, `Sandbox`, semantic helpers).
- `astra/framework/LICENSE` — MIT.
- Root `.env.example` — `GOOGLE_API_KEY`, logging, optional integrations.
- `astra/framework/pyproject.toml` — packaging metadata; `[project.urls]` present (currently `github.com/HeeManSu/astra-agi` — align with final public repo URL).

### Not done (launch blockers)

| Gap | Action |
|-----|--------|
| Root `README.md` | Day 3 |
| `docs/research.md` §4–6 | Day 2 — experiments, setup, results, limitations, conclusion (§1–3 + diagram exist) |
| Benchmark scripts + headline numbers | Day 2 — see below |
| `quickstart.py` at repo root | Day 1 |
| `CONTRIBUTING.md` | Day 3 |
| GitHub Actions (`pytest` on push) | Day 3 |
| PyPI publish (`astra-framework` / `astra-runtime`) | When ready; local `uv pip install -e` works from packages |

**Headline rule:** Abstract claims **3 LLM calls vs 13** on the investment task — **re-measure** with the benchmark harness; if numbers differ, update abstract, README table, and social copy.

---

## Day 1 — Code and packaging

### Morning — Cleanup

- Audit `astra/framework/src/framework/__init__.py` — expose only what’s needed (already lean; re-check after changes).
- Remove stray debug artifacts: no committed `test_tools.db`; `.debug/` is runtime output (gitignored). Don’t ship temp `.txt` / accidental DBs in examples.
- Ensure `.env.example` lists every key required by the investment example and optional server paths.
- Confirm `astra/framework/LICENSE` is MIT (done).

### Afternoon — Packaging

- Tidy `astra/framework/pyproject.toml`: `name`, `version`, `description`, readme, license.
- Set `[project.urls]` to the **final** public repo (Homepage, Repository, Issues).
- Verify: `cd astra/framework && uv pip install -e .` (or workspace install from repo root per your workflow).
- Add **`quickstart.py` at repo root** (~30 lines): runs the investment-team flow end-to-end against `astra/runtime/examples/investment_team/` (or a thin wrapper).

### Evening — Tests

- `uv run pytest astra/framework/tests/ -v`
- `uv run pytest astra/runtime/tests/ -v`
- Fix failures only (no new tests unless required to fix breakage).

---

## Day 2 — Research paper and benchmarks

**Priority:** Benchmarks are the headline; the paper is credibility.

### `docs/research.md` — fill gaps

- **§4 Experiments:** Benchmark task — e.g. investment analysis **AAPL** full run, same user prompt across frameworks.
- **§4 Setup:** Model(s), temperature, tool set, hardware/OS, library versions, seed policy if any.
- **§4 Results:** **Astra vs Agno `coordinate_team` vs CrewAI crew** on the **same query**.
  - Metrics: **LLM call count**, **total tokens** (if available), **wall-clock time**.
  - Run each **3×**, report **mean** (and optionally stdev).
- **§5 Limitations:** e.g. no parallel execution yet, single-level nesting only, no streaming mid-execution — be explicit.
- **§6 Conclusion:** One tight paragraph.
- **§2.5 table:** Re-read positioning table; add or link a **separate results table** with measured numbers (not only qualitative comparison).

### Benchmark harness (create)

Add something like:

`astra/runtime/examples/investment_team/benchmark/` **or** `projects/investment-team/benchmark/` (pick one; avoid duplicate logic)

Scripts (each accepts e.g. `--ticker AAPL`):

| Script | Role |
|--------|------|
| `run_astra.py` | Astra / Sandbox path for the runtime example |
| `run_agno.py` | `cookbook/agno-investment-team` equivalent |
| `run_crewai.py` | `cookbook/crewai-investment-team` equivalent |

Each prints at minimum: `LLM calls`, `Tokens` (or `N/A` if not instrumented yet), `Time (s)`, and a short `Output` snippet.

**Workflow:**

```bash
# Example — adjust paths after scripts exist
uv run python astra/runtime/examples/investment_team/benchmark/run_astra.py --ticker AAPL
uv run python path/to/run_agno.py --ticker AAPL
uv run python path/to/run_crewai.py --ticker AAPL
```

Update README and paper with the **one number** that matters (e.g. “13 → 3” **only if** measured).

---

## Day 3 — GitHub and README

### Root `README.md`

Target structure:

1. **Title:** Astra — compiler-based AI orchestration (or your final positioning line).
2. **One-liner:** Problem it solves.
3. **Benchmark table** (Astra vs Agno vs CrewAI) — from Day 2 runs.
4. **Quick install** (uv / pip from repo or PyPI when published).
5. **5-line code example** pointing at real imports.
6. Link to **`docs/research.md`**.
7. Link to **investment example** (`astra/runtime/examples/investment_team/`).
8. **Architecture:** mermaid from `docs/research.md` (Figure 1) or embed/link.

### GitHub prep

- Public repo: e.g. `github.com/HeeManSu/astra` (align `pyproject` URLs).
- Topics: `ai-agents`, `llm`, `multi-agent`, `compiler`, `python`.
- Pin or feature the investment example in the readme.
- **`CONTRIBUTING.md`** — short (two paragraphs): how to run tests, how to open issues/PRs.

### CI

- `.github/workflows/ci.yml` — on push/PR: checkout, install uv, `pytest` for `astra/framework/tests` and `astra/runtime/tests` (keep minimal).

---

## Day 4 — Launch

### LinkedIn (draft Day 3, post Day 4 morning IST)

- **Hook:** e.g. reduced LLM calls in multi-agent runs (use **measured** delta).
- **Body:** ReAct cost vs upfront plan; compiler metaphor; benchmark table; links to repo + paper.
- **CTA:** Open source — try it, break it, feedback welcome.

### X / Twitter thread

1. Hook + benchmark numbers (table screenshot).
2. Architecture diagram from `docs/research.md`.
3. 5-line example.
4. “Paper + code” link.

### Distribution

- Subreddits: e.g. r/MachineLearning, r/LocalLLaMA, r/Python (follow each sub’s rules).
- Hacker News: “Show HN: Astra — …” with measured one-liner.

---

## Checklist (copy-paste)

- [ ] Day 1: cleanup, `quickstart.py`, packaging URLs, tests green
- [ ] Day 2: benchmark scripts, 3× runs, `docs/research.md` §4–6, headline number verified
- [ ] Day 3: root README, CONTRIBUTING, CI, repo public + topics
- [ ] Day 4: LinkedIn, X thread, Reddit/HN (where appropriate)
