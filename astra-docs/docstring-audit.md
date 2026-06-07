# Docstring audit

This file tracks docstring coverage for the public surface of the three
Astra packages. Each section lists the public submodules whose symbols
must have a Google-style docstring with `Args`, `Returns`, and (where
applicable) `Raises` sections.

To populate this with concrete misses for a package, run:

```bash
python astra-docs/scripts/build-reference.py --package framework --check
python astra-docs/scripts/build-reference.py --package runtime --check
python astra-docs/scripts/build-reference.py --package observability --check
```

Each invocation prints the fully-qualified names of symbols that are
exported via `__all__` (or otherwise public) but lack a non-empty
description. CI mirrors that command on every pull request and posts a
sticky comment with the report; see
`.github/workflows/reference.yml`.

> **Note** -- the checkboxes below are scaffolding only. The first CI
> run will replace this file (or attach a comment) with concrete misses.

---

## astra-framework

- [ ] `agents` -- `Agent`, agent configuration, lifecycle hooks
- [ ] `team` -- `Team`, coordinator/parallel/sequential/hierarchical topologies
- [ ] `tool` -- `@tool` decorator, `Tool` base, tool-result schemas
- [ ] `models` -- model adapters (OpenAI, Anthropic, Google, Bedrock, Azure, self-hosted)
- [ ] `memory` -- `Memory` interface and built-in backends
- [ ] `storage` -- session/message/artifact storage backends
- [ ] `middleware` -- pre/post hooks, guardrails, retries, cost budgeting
- [ ] `rag` -- retrievers, chunkers, embedders, `RAGPipeline`
- [ ] `code_mode` -- code-execution sandbox, `CodeAgent`

## astra-runtime

- [ ] `server` -- `AstraServer` entry point, Uvicorn integration
- [ ] `app` -- `create_app()` factory and lifecycle hooks
- [ ] `routes` -- REST and WebSocket route handlers
- [ ] `auth` -- API key, JWT, OAuth backends and the `AuthBackend` protocol
- [ ] `registry` -- `AgentRegistry`: lookup, registration, hot-reload
- [ ] `sync` -- worker-pool synchroniser and distributed-state helpers

## astra-observability

- [ ] `engine` -- `TracingEngine`
- [ ] `instrument` -- auto-instrumentation hooks
- [ ] `tracing` -- span types, status codes, OpenTelemetry bridge
- [ ] `storage` -- SQLite, Postgres, OTLP exporters
- [ ] `query` -- query DSL and helpers
- [ ] `streaming` -- `EventStream` for live trace consumers
- [ ] `debug` -- Playground / CLI debug helpers

---

## Style guide reminders

1. **Use Google style.** Sections: `Args`, `Returns`, `Raises`, `Examples`,
   `Notes`, `Warnings`. The walker recognises all of these.
2. **Type everything.** Annotations on parameters and return types are
   surfaced in the generated MDX; missing ones leave a gap.
3. **Be terse.** The first paragraph is shown verbatim under the symbol
   heading; keep it to a single sentence where possible.
4. **`__all__` is the contract.** Anything not in `__all__` (when the
   module declares one) is excluded from the reference even if it has a
   docstring.
5. **Don't re-document inherited methods.** The walker reads each class
   in isolation; rely on the parent class's docstring rather than copying
   it.
