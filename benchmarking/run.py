"""Benchmark orchestrator.

For each (framework, query, trial), runs the framework's `run.py` in its
own subprocess and uv venv. Each trial enables the framework's native
verbose logging and captures full per-call SDK request/response payloads
to `runs/<framework>/<query>_trial<N>/`. Resumable via existing
`result.json` files.

Usage:
    uv run --project agno-investment-team python run.py --framework agno
    uv run --project agno-investment-team python run.py --framework agno --queries Q7 --trials 1
    uv run --project agno-investment-team python run.py --framework agno --force
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


BENCH_ROOT = Path(__file__).resolve().parent
RUNS_DIR = BENCH_ROOT / "runs"

ALL_QUERIES = ("Q1", "Q2", "Q3", "Q6", "Q7", "Q9")

# Each framework directory must contain a run.py with the same
# CLI contract (--query Q --trial N --out-dir <path>).
SIDE_DIR = {
    "agno": BENCH_ROOT / "agno-investment-team",
    "autogen": BENCH_ROOT / "autogen-investment-team",
    "crewai": BENCH_ROOT / "crewai-investment-team",
    "langgraph": BENCH_ROOT / "langgraph-investment-team",
    "astra": BENCH_ROOT / "astra-invesment-team",
}


def _clean_env() -> dict:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)  # let uv pick the per-project venv
    return env


def trial_out_dir(framework: str, query: str, trial: int) -> Path:
    return RUNS_DIR / framework / f"{query}_trial{trial}"


def already_done(framework: str, query: str, trial: int) -> bool:
    return (trial_out_dir(framework, query, trial) / "result.json").exists()


def run_trial(framework: str, query: str, trial: int) -> dict | None:
    side = SIDE_DIR[framework]
    out_dir = trial_out_dir(framework, query, trial)
    print(f"[{framework}/{query}/trial{trial}] running ...", end=" ", flush=True)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "run.py",
                "--query",
                query,
                "--trial",
                str(trial),
                "--out-dir",
                str(out_dir),
            ],
            cwd=side.as_posix(),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=1200,  # 20 min per trial — agno can be slow under load
        )
    except subprocess.TimeoutExpired:
        dt = time.perf_counter() - t0
        print(f"TIMEOUT after {dt:.0f}s — moving on")
        return None
    dt = time.perf_counter() - t0
    if proc.returncode != 0:
        print(f"FAILED in {dt:.1f}s")
        sys.stderr.write(proc.stderr[-2000:] + "\n")
        return None
    result_path = out_dir / "result.json"
    if not result_path.exists():
        print(f"NO result.json after {dt:.1f}s")
        return None
    result = json.loads(result_path.read_text())
    print(
        f"ok in {dt:.1f}s  calls={result['num_llm_calls']}  tokens={result['total_tokens']}",
        flush=True,
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--framework", choices=list(SIDE_DIR.keys()), required=True)
    p.add_argument("--queries", nargs="+", choices=ALL_QUERIES, default=list(ALL_QUERIES))
    p.add_argument("--trials", type=int, default=3)
    p.add_argument("--force", action="store_true", help="re-run trials with existing result.json")
    p.add_argument("--sleep", type=float, default=2.0, help="seconds between trials")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    # Build the matrix
    matrix = [(args.framework, q, t) for q in args.queries for t in range(args.trials)]
    if args.dry_run:
        print(f"Matrix: {len(matrix)} trials")
        for fw, q, t in matrix:
            done = already_done(fw, q, t) and not args.force
            print(f"  [{'SKIP' if done else 'TODO'}] {fw}/{q}/trial{t}")
        return 0

    pending = [(fw, q, t) for (fw, q, t) in matrix if args.force or not already_done(fw, q, t)]
    skipped = len(matrix) - len(pending)
    print(f"Matrix: {len(matrix)} trials  Pending: {len(pending)}  Skipped (cached): {skipped}")

    all_results: list[dict] = []
    for i, (fw, q, t) in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] ", end="")
        result = run_trial(fw, q, t)
        if result:
            all_results.append(result)
        if i < len(pending) and args.sleep > 0:
            time.sleep(args.sleep)

    print()
    if not all_results:
        print("(no new results — all cached or all failed)")
        return 0

    # Print quick per-query mean
    by_q: dict[str, list[dict]] = {}
    for r in all_results:
        by_q.setdefault(r["query_id"], []).append(r)
    print(f"\n{'query':6s} {'n':>3s} {'calls':>7s} {'tokens':>10s} {'wall_s':>8s}")
    print("-" * 40)
    for q in sorted(by_q):
        rows = by_q[q]
        n = len(rows)
        avg_calls = sum(r["num_llm_calls"] for r in rows) / n
        avg_tokens = sum(r["total_tokens"] for r in rows) / n
        avg_wall = sum(r["wall_ms"] for r in rows) / n / 1000
        print(f"{q:6s} {n:3d} {avg_calls:7.1f} {avg_tokens:10,.0f} {avg_wall:8.1f}")
    print()
    print(f"All outputs under: {RUNS_DIR}/{args.framework}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
