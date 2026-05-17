"""Single-trial runner for the AutoGen research team.

  1. AutoGen v0.7 has no global `debug_mode` flag (it is quiet by default).
     Instead, after the run completes we iterate the SelectorGroupChat's
     full `result.messages` stream and print each message (with its source,
     type, and content) to stdout. That gives the same per-agent visibility
     Agno's `debug_mode=True` provides.
  2. Every `google.genai` SDK call is captured by TokenCounter, which dumps
     the full request payload, full response, and `usage_metadata` to JSON.

Retry-on-empty: if SelectorGroupChat returns an empty stitched packet (which
can happen on transient Gemini errors), the run is retried up to 3 times.

Outputs (one directory per trial):
    runs/autogen/<query>_trial<N>/
        autogen.log            tee'd stdout (post-run message stream)
        call_NNN_request.json        full request payload per LLM call
        call_NNN_response.json       full response per LLM call
        summary.json                 per-trial token totals + per-call breakdown
        response.txt                 the framework's final stitched response
        result.json                  one-line trial summary (includes attempts_used)

Usage:
    cd benchmarking/autogen-investment-team
    uv run python run.py --query Q7 --trial 0
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
BENCH_ROOT = HERE.parent
REPO_ROOT = BENCH_ROOT.parent

DEFAULT_OUT_ROOT = BENCH_ROOT / "runs" / "autogen"

# Load .env from this project, then the repo root (root API key wins).
for env in (HERE / ".env", REPO_ROOT / ".env"):
    if env.exists():
        load_dotenv(env, override=True)

# Shared TokenCounter lives in benchmarking/harness/.
sys.path.insert(0, str(BENCH_ROOT / "harness"))

# Queries — shared across all five frameworks' run.py files.
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


_SECTION_HEADERS = {
    "MacroStrategist":    "## 1. MACRO ANALYSIS",
    "FinancialAnalyst":   "## 2. FINANCIAL ANALYSIS",
    "ValuationAnalyst":   "## 3. VALUATION ANALYSIS",
    "TechnicalAnalyst":   "## 4. TECHNICAL ANALYSIS",
}
_ORDER = ("MacroStrategist", "FinancialAnalyst", "ValuationAnalyst", "TechnicalAnalyst")


def _stitch_packet(messages) -> str:
    """Pull the LAST non-empty text message from each analyst, format as a
    four-section research packet — same shape Astra/Agno/CrewAI/LangGraph
    return so the downstream quality review sees what each framework produced.
    """
    by_agent: dict[str, str] = {}
    for m in messages:
        src = getattr(m, "source", None)
        if src not in _SECTION_HEADERS:
            continue
        content = getattr(m, "content", None)
        if isinstance(content, str) and content.strip():
            by_agent[src] = content.strip()

    parts = []
    for name in _ORDER:
        header = _SECTION_HEADERS[name]
        body = by_agent.get(name, "(no output)")
        parts.append(f"{header}\n\n{body}")
    return "\n\n---\n\n".join(parts)


def _format_message(msg) -> str:
    """Format one SelectorGroupChat message for the log."""
    src = getattr(msg, "source", "?")
    kind = type(msg).__name__
    content = getattr(msg, "content", None)
    if isinstance(content, str):
        body = content
    elif isinstance(content, list):
        body = "\n".join(repr(part) for part in content)
    else:
        body = repr(content)
    return f"[{kind} from {src}]\n{body}\n"


async def _arun(query_text: str) -> tuple[str, list]:
    # Imported here so TokenCounter is patched before the team's client is built.
    from teams import research_team

    await research_team.reset()
    result = await research_team.run(task=query_text)
    return _stitch_packet(result.messages), result.messages


async def _arun_with_retry(query_text: str, max_attempts: int = 3) -> tuple[str, list, int]:
    """Run the team; retry up to `max_attempts` if the stitched response comes
    back empty (silent failure on transient Gemini errors). Returns
    (response, messages, attempts_used).
    """
    response = ""
    messages: list = []
    for attempt in range(1, max_attempts + 1):
        try:
            response, messages = await _arun(query_text)
        except Exception:
            if attempt == max_attempts:
                raise
            response = ""
            messages = []
        if response and response.strip():
            return response, messages, attempt
        if attempt < max_attempts:
            print(f"\n[autogen] empty response on attempt {attempt}; retrying...\n", flush=True)
            await asyncio.sleep(2.0)
    return response, messages, max_attempts


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", choices=list(QUERIES.keys()), default="Q7")
    parser.add_argument("--trial", type=int, default=0)
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Override output dir. Default: runs/autogen/<query>_trial<N>/")
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
    # Clean previous dumps so call indices restart at 1.
    for f in out_dir.glob("call_*.json"):
        f.unlink()
    for f in out_dir.glob("summary.json"):
        f.unlink()

    log_path = out_dir / "autogen.log"
    print(f"[autogen] query={query_id} trial={args.trial}")
    print(f"[autogen] out_dir={out_dir}")
    print(f"[autogen] {query_id}: {query_text[:100]}...")
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

    messages: list = []
    attempts_used = 1
    try:
        with TokenCounter(out_dir=out_dir, log_fp=log_fp) as counter:
            try:
                response, messages, attempts_used = asyncio.run(_arun_with_retry(query_text))
                ok = bool(response and response.strip())
                err = None if ok else "empty_response_after_retries"
            except Exception as e:  # noqa: BLE001
                response = ""
                ok = False
                err = f"{type(e).__name__}: {e}"

        # Dump the SelectorGroupChat message stream post-run (AutoGen v0.7 is
        # quiet during execution — this is the closest equivalent to Agno's
        # debug_mode stream).
        print()
        print("=" * 72)
        print("AUTOGEN MESSAGE STREAM (post-run)")
        print("=" * 72)
        for i, m in enumerate(messages):
            print(f"\n----- message {i:3d} -----")
            print(_format_message(m))
    finally:
        sys.stdout = real_stdout
        sys.stderr = real_stderr
        log_fp.close()
    wall_ms = (time.perf_counter() - t0) * 1000

    summary = counter.summary
    summary_path = write_summary(out_dir, summary)

    (out_dir / "response.txt").write_text(response or "")
    import json
    (out_dir / "result.json").write_text(json.dumps({
        "framework":         "autogen",
        "query_id":          query_id,
        "trial":             args.trial,
        "ok":                ok,
        "error":             err,
        "attempts_used":     attempts_used,
        "num_llm_calls":     summary.num_calls,
        "prompt_tokens":     summary.prompt_tokens,
        "completion_tokens": summary.completion_tokens,
        "thoughts_tokens":   summary.thoughts_tokens,
        "total_tokens":      summary.total_tokens,
        "wall_ms":           round(wall_ms, 2),
        "llm_latency_ms":    round(summary.llm_latency_ms, 2),
        "response_chars":    len(response or ""),
    }, indent=2))

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
