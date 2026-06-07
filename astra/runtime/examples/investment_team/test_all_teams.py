"""
All-Teams Integration Test — Investment Team Example

Tests all 4 team modes (coordinate, route, broadcast, task) with 10 investment
prompts each. Streams from POST /teams/{team_id}/stream, collects SSE events,
and validates responses exist. Reports all results at the end.

Run:
    cd astra/runtime
    uv run python examples/investment_team/test_all_teams.py
"""

from dataclasses import dataclass, field
import json
import os
import sys
import time
import traceback

import httpx


# Logging to file + stdout
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_all_teams_results.log")
_log_fh = open(LOG_FILE, "w", encoding="utf-8")


def log(msg: str = ""):
    """Write to both stdout and log file."""
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()
    _log_fh.write(msg + "\n")
    _log_fh.flush()


# Config
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
STREAM_TIMEOUT = 600

TEAMS = [
    "coordinate-team",
    "route-team",
    "broadcast-team",
    "task-team",
]

PROMPTS = [
    "Should I invest in nvidia?",
    "What is the current stock price of Apple?",
    "Analyze the risk profile of Tesla stock",
    "Compare Microsoft and Google fundamentals",
    "What are the latest analyst recommendations for Amazon?",
    "Give me a technical analysis of Meta stock",
    "What is the financial health of JPMorgan Chase?",
    "Should I buy or sell Netflix based on recent performance?",
    "What are the key financial ratios for Berkshire Hathaway?",
    "Assess the market outlook for the semiconductor sector focusing on AMD",
]


@dataclass
class TestResult:
    team_id: str
    prompt: str
    success: bool
    content: str = ""
    content_length: int = 0
    error: str = ""
    duration_s: float = 0.0
    tool_calls: int = 0
    event_types: list = field(default_factory=list)


def stream_team(team_id: str, query: str) -> dict:
    url = f"{BASE_URL}/teams/{team_id}/stream"
    payload = {"message": query}
    events = []
    content_parts = []
    errors = []
    tool_count = 0

    with httpx.Client(timeout=httpx.Timeout(STREAM_TIMEOUT)) as client:
        with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    event = json.loads(data_str)
                    events.append(event)
                    etype = event.get("event_type", "")
                    if etype == "content":
                        text = event.get("data", {}).get("text", "")
                        content_parts.append(text)
                    elif etype == "error":
                        errors.append(event.get("data", {}).get("message", ""))
                    elif etype == "tool_call":
                        tool_count += 1
                except json.JSONDecodeError:
                    pass

    return {
        "events": events,
        "content": "\n".join(content_parts),
        "errors": errors,
        "tool_count": tool_count,
        "event_types": [e.get("event_type") for e in events],
    }


def run_all_tests() -> list[TestResult]:
    results: list[TestResult] = []
    total = len(TEAMS) * len(PROMPTS)
    current = 0

    log("=" * 80)
    log("ALL-TEAMS INTEGRATION TEST")
    log(f"Teams: {len(TEAMS)} | Prompts: {len(PROMPTS)} | Total: {total} tests")
    log(f"Server: {BASE_URL}")
    log("=" * 80)

    for team_id in TEAMS:
        log(f"\n{'─' * 80}")
        log(f"TEAM: {team_id}")
        log(f"{'─' * 80}")

        for i, prompt in enumerate(PROMPTS):
            current += 1
            short_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
            log(f'\n  [{current}/{total}] {team_id} | "{short_prompt}"')

            start = time.time()
            result = TestResult(team_id=team_id, prompt=prompt, success=False)

            try:
                stream_result = stream_team(team_id, prompt)
                duration = time.time() - start
                result.duration_s = round(duration, 1)
                result.event_types = stream_result["event_types"]
                result.tool_calls = stream_result["tool_count"]

                if stream_result["errors"]:
                    result.error = "; ".join(stream_result["errors"])
                    log(f"    ❌ ERROR ({result.duration_s}s): {result.error[:100]}")
                elif not stream_result["content"]:
                    result.error = "No content in response"
                    log(f"    ❌ NO CONTENT ({result.duration_s}s)")
                else:
                    result.success = True
                    result.content = stream_result["content"]
                    result.content_length = len(result.content)
                    log(
                        f"    ✅ OK ({result.duration_s}s) — {result.content_length} chars, {result.tool_calls} tools"
                    )

            except httpx.HTTPStatusError as e:
                duration = time.time() - start
                result.duration_s = round(duration, 1)
                result.error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                log(f"    ❌ HTTP ERROR ({result.duration_s}s): {result.error[:100]}")
            except httpx.ReadTimeout:
                duration = time.time() - start
                result.duration_s = round(duration, 1)
                result.error = f"Timeout after {STREAM_TIMEOUT}s"
                log(f"    ❌ TIMEOUT ({result.duration_s}s)")
            except Exception as e:
                duration = time.time() - start
                result.duration_s = round(duration, 1)
                result.error = f"{type(e).__name__}: {e}"
                log(f"    ❌ EXCEPTION ({result.duration_s}s): {result.error[:100]}")
                traceback.print_exc()

            results.append(result)

    return results


def print_report(results: list[TestResult]):
    log()
    log()
    log("=" * 80)
    log("FINAL RESULTS REPORT")
    log("=" * 80)

    for team_id in TEAMS:
        team_results = [r for r in results if r.team_id == team_id]
        passed = sum(1 for r in team_results if r.success)
        avg_dur = sum(r.duration_s for r in team_results) / max(len(team_results), 1)
        avg_ch = sum(r.content_length for r in team_results if r.success) / max(passed, 1)
        ttl_tools = sum(r.tool_calls for r in team_results)

        log(f"\n{'─' * 80}")
        log(
            f"  {team_id}: {passed}/{len(team_results)} passed | avg {avg_dur:.0f}s | avg {avg_ch:.0f} chars | {ttl_tools} tools"
        )
        log(f"{'─' * 80}")

        for r in team_results:
            st = "✅" if r.success else "❌"
            short = r.prompt[:45] + "..." if len(r.prompt) > 45 else r.prompt
            if r.success:
                log(
                    f"  {st} [{r.duration_s:>5.1f}s] {short} → {r.content_length} chars, {r.tool_calls} tools"
                )
            else:
                log(f"  {st} [{r.duration_s:>5.1f}s] {short} → {r.error[:60]}")

    total = len(results)
    passed = sum(1 for r in results if r.success)
    total_dur = sum(r.duration_s for r in results)

    log(f"\n{'=' * 80}")
    log(
        f"OVERALL: {passed}/{total} passed ({passed / total * 100:.0f}%) | Total time: {total_dur / 60:.1f} min"
    )
    log(f"{'=' * 80}")

    # Print all successful outputs
    successful = [r for r in results if r.success]
    if successful:
        log(f"\n\n{'=' * 80}")
        log(f"SUCCESSFUL OUTPUTS ({len(successful)} results)")
        log(f"{'=' * 80}")

        for r in successful:
            log(f"\n{'─' * 80}")
            log(f"Team: {r.team_id}")
            log(f"Prompt: {r.prompt}")
            log(f"Duration: {r.duration_s}s | Tools: {r.tool_calls} | Chars: {r.content_length}")
            log(f"{'─' * 80}")
            if len(r.content) > 2000:
                log(r.content[:2000])
                log(f"\n... ({len(r.content) - 2000} more chars)")
            else:
                log(r.content)

    failed_results = [r for r in results if not r.success]
    if failed_results:
        log(f"\n\n{'=' * 80}")
        log(f"FAILED TESTS ({len(failed_results)} failures)")
        log(f"{'=' * 80}")
        for r in failed_results:
            log(f"\n  Team: {r.team_id}")
            log(f"  Prompt: {r.prompt}")
            log(f"  Error: {r.error}")

    return passed == total


if __name__ == "__main__":
    log(f"Test started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Log file: {LOG_FILE}")
    results = run_all_tests()
    all_passed = print_report(results)
    _log_fh.close()
    sys.exit(0 if all_passed else 1)
