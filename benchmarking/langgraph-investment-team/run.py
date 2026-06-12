"""Single-trial runner for the LangGraph research graph.

  1. LangChain's NATIVE debug + verbose flags are flipped on. STDOUT-only;
     does not change what the model receives.
  2. Every `google.genai` SDK call is captured by TokenCounter, which dumps
     the full request payload, full response, and `usage_metadata` to JSON.

Retry-on-empty: if the graph returns an empty `final_report` (transient
Gemini error), retry up to 3 times.

Outputs (one directory per trial):
    runs/langgraph/<query>_trial<N>/
        langgraph.log          tee'd stdout (LangChain chain/tool stream)
        call_NNN_request.json        full request payload per LLM call
        call_NNN_response.json       full response per LLM call
        summary.json                 per-trial token totals + per-call breakdown
        response.txt                 the graph's final_report
        result.json                  one-line trial summary (includes attempts_used)

Usage:
    cd benchmarking/langgraph-investment-team
    uv run python run.py --query Q7 --trial 0
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
BENCH_ROOT = HERE.parent
REPO_ROOT = BENCH_ROOT.parent

DEFAULT_OUT_ROOT = BENCH_ROOT / "runs" / "langgraph"

for env in (HERE / ".env", REPO_ROOT / ".env"):
    if env.exists():
        load_dotenv(env, override=True)

os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGSMITH_TRACING", "false")

sys.path.insert(0, str(BENCH_ROOT / "harness"))

QUERIES = {
    "Q1": "Analyze AAPL and produce a full research report.",
    "Q2": "Analyze MSFT and produce a full research report.",
    "Q3": "Analyze NVDA and produce a full research report.",
    "Q6": "Compare AAPL and MSFT head-to-head and produce a research report recommending which one is the better investment today.",
    "Q7": (
        "Compare AAPL, MSFT, and GOOGL head-to-head and produce a research "
        "report ranking them from best to worst investment today, with "
        "specific reasoning from each of macro, fundamentals, valuation, "
        "and technicals."
    ),
    "Q9": "Analyze TSLA. If the macro regime is risk-off, focus your final verdict on downside scenarios and stop-loss levels. If risk-on, emphasize upside targets and momentum.",
}


def _enable_langchain_logging() -> None:
    import langchain

    langchain.debug = True
    langchain.verbose = True


def _run(query_text: str) -> str:
    from graph import research_graph

    _enable_langchain_logging()
    final_state = research_graph.invoke({"query": query_text})
    return final_state.get("final_report", "") or ""


def _run_with_retry(query_text: str, max_attempts: int = 3) -> tuple[str, int]:
    response = ""
    for attempt in range(1, max_attempts + 1):
        try:
            response = _run(query_text)
        except Exception:
            if attempt == max_attempts:
                raise
            response = ""
        if response and response.strip():
            return response, attempt
        if attempt < max_attempts:
            print(f"\n[langgraph] empty response on attempt {attempt}; retrying...\n", flush=True)
            time.sleep(2.0)
    return response, max_attempts


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", choices=list(QUERIES.keys()), default="Q7")
    parser.add_argument("--trial", type=int, default=0)
    parser.add_argument(
        "--out-dir", type=str, default=None, help="Override output dir. Default: runs/langgraph/<query>_trial<N>/"
    )
    args = parser.parse_args()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) not set.", file=sys.stderr)
        return 2

    from harness.counter import TokenCounter, write_summary

    query_id = args.query
    query_text = QUERIES[query_id]

    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
    else:
        out_dir = DEFAULT_OUT_ROOT / f"{query_id}_trial{args.trial}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("call_*.json"):
        f.unlink()
    for f in out_dir.glob("summary.json"):
        f.unlink()

    log_path = out_dir / "langgraph.log"
    print(f"[langgraph] query={query_id} trial={args.trial}")
    print(f"[langgraph] out_dir={out_dir}")
    print(f"[langgraph] {query_id}: {query_text[:100]}...")
    print()

    t0 = time.perf_counter()
    log_fp = log_path.open("w")

    class _Tee:
        def __init__(self, *streams):
            self._streams = streams

        def write(self, data):
            for s in self._streams:
                try:
                    s.write(data)
                except Exception:
                    pass

        def flush(self):
            for s in self._streams:
                try:
                    s.flush()
                except Exception:
                    pass

    real_stdout = sys.stdout
    real_stderr = sys.stderr
    sys.stdout = _Tee(real_stdout, log_fp)
    sys.stderr = _Tee(real_stderr, log_fp)
    attempts_used = 1
    try:
        with TokenCounter(out_dir=out_dir, log_fp=log_fp) as counter:
            try:
                response, attempts_used = _run_with_retry(query_text)
                ok = bool(response and response.strip())
                err = None if ok else "empty_response_after_retries"
            except Exception as e:  # noqa: BLE001
                response = ""
                ok = False
                err = f"{type(e).__name__}: {e}"
    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr
        log_fp.close()
    wall_ms = (time.perf_counter() - t0) * 1000

    summary = counter.summary
    summary_path = write_summary(out_dir, summary)

    (out_dir / "response.txt").write_text(response or "")
    import json

    (out_dir / "result.json").write_text(
        json.dumps(
            {
                "framework": "langgraph",
                "query_id": query_id,
                "trial": args.trial,
                "ok": ok,
                "error": err,
                "attempts_used": attempts_used,
                "num_llm_calls": summary.num_calls,
                "prompt_tokens": summary.prompt_tokens,
                "completion_tokens": summary.completion_tokens,
                "thoughts_tokens": summary.thoughts_tokens,
                "total_tokens": summary.total_tokens,
                "wall_ms": round(wall_ms, 2),
                "llm_latency_ms": round(summary.llm_latency_ms, 2),
                "response_chars": len(response or ""),
            },
            indent=2,
        )
    )

    print()
    print("=" * 72)
    print("PER-CALL BREAKDOWN (SDK-reported)")
    print("=" * 72)
    for c in summary.calls:
        n_tools = len(c.tool_calls)
        preview = (c.text_preview or "")[:60].replace("\n", " ")
        print(
            f"  call {c.call_index:3d}  prompt={c.prompt_tokens:6d}  completion={c.completion_tokens:6d}  "
            f"thoughts={c.thoughts_tokens:5d}  total={c.total_tokens:6d}  "
            f"tools={n_tools}  {preview!r}"
        )

    print()
    print("=" * 72)
    print("SDK-REPORTED TOTALS")
    print("=" * 72)
    print(f"  ok                : {ok}")
    if err:
        print(f"  error             : {err}")
    print(f"  llm_calls         : {summary.num_calls}")
    print(f"  prompt_tokens     : {summary.prompt_tokens:,}")
    print(f"  completion_tokens : {summary.completion_tokens:,}")
    print(f"  thoughts_tokens   : {summary.thoughts_tokens:,}")
    print(f"  total_tokens      : {summary.total_tokens:,}")
    print(f"  llm_latency_ms    : {summary.llm_latency_ms:,.0f}")
    print(f"  wall_ms           : {wall_ms:,.0f}")
    print(f"  response_chars    : {len(response or '')}")
    print(f"  attempts_used     : {attempts_used}")
    print()
    print(f"  per-trial out_dir: {out_dir}")
    print(f"  summary           : {summary_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
