"""
Integration Test — Coordinate Team: "Should I invest in nvidia?"

Hits the live server's POST /teams/coordinate-team/stream endpoint,
collects the streamed response, then uses an LLM call to compare the
output against a reference for structural and semantic match.

Run:
    cd astra/runtime
    uv run python examples/investment_team/test_coordinate_team.py
"""

import json
import os
import sys
import traceback

import httpx


# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
TEAM_ID = "coordinate-team"
USER_QUERY = "Should I invest in nvidia?"
STREAM_TIMEOUT = 600  # 10 minutes

# Load API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    try:
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        load_dotenv(env_path, override=True)
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    except Exception:
        pass

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY not set", flush=True)
    sys.exit(1)

import google.generativeai as genai


genai.configure(api_key=GOOGLE_API_KEY)

# ── Reference Output ───────────────────────────────────────────────────────
REFERENCE_OUTPUT = """\
NVIDIA (NVDA) presents a compelling investment opportunity, primarily driven by \
its dominant position in the AI semiconductor market.

Financial Performance: NVIDIA has demonstrated exceptional financial performance, \
characterized by explosive revenue growth, particularly in its Data Center segment. \
The company maintains strong gross and operating margins due to high demand and \
specialized hardware, coupled with its robust CUDA software ecosystem.

Market Position and Growth Opportunities: NVIDIA holds an estimated 85%+ market \
share in AI training GPUs with growth opportunities including enterprise AI adoption, \
the Blackwell architecture upgrade cycle, sovereign AI initiatives, and increasing \
demand for AI inference workloads.

Competitive Landscape and Risks: While NVIDIA faces competition from AMD and Intel, \
its CUDA ecosystem provides a significant competitive advantage. Risks include custom \
AI silicon by cloud providers, economic downturns, and geopolitical tensions.

The Risk Officer has assessed the overall risk profile as Moderate to High. Key risks \
include geopolitical and supply chain dependence, intense competition, and economic \
sensitivity with valuation risk.

Recommendation: Invest a meaningful allocation (e.g., $1.5M-$2.5M) in NVIDIA (NVDA), \
reflecting a bullish outlook while acknowledging the elevated risk profile.

An investment memorandum has been prepared and saved.
"""


def stream_coordinate_team(query: str) -> dict:
    """POST to /teams/{team_id}/stream and collect all SSE events."""
    url = f"{BASE_URL}/teams/{TEAM_ID}/stream"
    payload = {"message": query}

    events = []
    content_parts = []
    errors = []

    print(f"   Connecting to {url} ...", flush=True)

    with httpx.Client(timeout=httpx.Timeout(STREAM_TIMEOUT)) as client:
        with client.stream("POST", url, json=payload) as response:
            print(f"   Status: {response.status_code}", flush=True)
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
                    elif etype in ("status", "code_generated"):
                        msg = event.get("data", {}).get("message", "")
                        print(f"   [{etype}] {msg}", flush=True)
                    elif etype == "tool_call":
                        tool = event.get("data", {}).get("tool_name", "?")
                        args = event.get("data", {}).get("arguments", {})
                        print(f"   [tool_call] {tool}({json.dumps(args)[:80]})", flush=True)
                    elif etype == "tool_result":
                        tool = event.get("data", {}).get("tool_name", "?")
                        success = event.get("data", {}).get("success", False)
                        print(f"   [tool_result] {tool} → {'✓' if success else '✗'}", flush=True)
                except json.JSONDecodeError:
                    pass

    return {
        "events": events,
        "content": "\n".join(content_parts),
        "errors": errors,
        "event_types": [e.get("event_type") for e in events],
    }


def llm_compare(actual: str, reference: str) -> dict:
    """Use Gemini to compare actual vs reference output."""
    prompt = f"""\
You are an expert evaluator. Compare these two investment analysis outputs.
They do NOT need to match word-for-word. Numbers, dollar amounts, and percentages
can differ. What matters is:

1. STRUCTURE: Does the actual output cover similar sections/topics?
   (financial analysis, market position, risks, recommendation)
2. MEANING: Does it convey a similar investment thesis?
   (analysis of NVIDIA, acknowledges risks, gives a recommendation)
3. COMPLETENESS: Does it include multi-perspective analysis?

REFERENCE OUTPUT:
---
{reference}
---

ACTUAL OUTPUT:
---
{actual}
---

Respond ONLY with valid JSON (no markdown fences):
{{
  "match": true or false,
  "score": 0.0 to 1.0,
  "reasoning": "brief explanation",
  "sections_found": {{
    "financial_analysis": true or false,
    "market_position": true or false,
    "risk_assessment": true or false,
    "investment_recommendation": true or false,
    "dollar_allocation": true or false,
    "nvidia_mentioned": true or false,
    "multiple_analysts_consulted": true or false,
    "memo_mentioned": true or false
  }}
}}

Score >= 0.70 means match. Set "match" to true if score >= 0.70.
"""

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "match": False,
            "score": 0.0,
            "reasoning": f"LLM returned unparsable response: {text[:500]}",
            "sections_found": {},
        }


def main():
    MAX_ATTEMPTS = 5

    print("=" * 70, flush=True)
    print("INTEGRATION TEST: Coordinate Team", flush=True)
    print(f"Query: '{USER_QUERY}'", flush=True)
    print(f"Server: {BASE_URL}", flush=True)
    print(f"Max attempts: {MAX_ATTEMPTS}", flush=True)
    print("=" * 70, flush=True)

    best_score = 0.0
    best_sections: dict = {}
    best_content = ""
    best_attempt = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n{'━' * 70}", flush=True)
        print(f"  ATTEMPT {attempt}/{MAX_ATTEMPTS}", flush=True)
        print(f"{'━' * 70}", flush=True)

        # Step 1: Stream
        print("\n[STEP 1] Streaming response from coordinate team...", flush=True)
        try:
            result = stream_coordinate_team(USER_QUERY)
        except Exception as e:
            print(f"\n❌ STREAM FAILED: {e}", flush=True)
            traceback.print_exc()
            if attempt < MAX_ATTEMPTS:
                print("\n   Retrying in 5 seconds...", flush=True)
                import time

                time.sleep(5)
                continue
            else:
                sys.exit(1)

        if result["errors"]:
            print("\n❌ STREAM ERRORS:", flush=True)
            for err in result["errors"]:
                print(f"   • {err}", flush=True)
            if attempt < MAX_ATTEMPTS:
                print("\n   Retrying...", flush=True)
                continue
            else:
                sys.exit(1)

        if not result["content"]:
            print("\n❌ NO CONTENT in response", flush=True)
            if attempt < MAX_ATTEMPTS:
                print("\n   Retrying...", flush=True)
                continue
            else:
                sys.exit(1)

        content = result["content"]
        print(f"\n   ✓ Got response ({len(content)} chars)", flush=True)
        print(f"   ✓ Event types: {result['event_types']}", flush=True)

        # Print output
        print(f"\n{'─' * 70}", flush=True)
        print("ACTUAL OUTPUT:", flush=True)
        print(f"{'─' * 70}", flush=True)
        print(content, flush=True)
        print(f"{'─' * 70}", flush=True)

        # Step 2: LLM comparison
        print("\n[STEP 2] Running LLM comparison...", flush=True)
        try:
            comparison = llm_compare(content, REFERENCE_OUTPUT)
        except Exception as e:
            print(f"\n❌ LLM COMPARISON FAILED: {e}", flush=True)
            traceback.print_exc()
            if attempt < MAX_ATTEMPTS:
                continue
            else:
                sys.exit(1)

        score = comparison.get("score", 0.0)
        match = comparison.get("match", False)
        reasoning = comparison.get("reasoning", "No reasoning")
        sections = comparison.get("sections_found", {})

        # Track best
        if score > best_score:
            best_score = score
            best_sections = sections
            best_content = content
            best_attempt = attempt

        print(f"\n   Score: {score:.0%}", flush=True)
        print(f"   Match: {'✅ YES' if match else '❌ NO'}", flush=True)
        print(f"   Reasoning: {reasoning}", flush=True)

        all_sections = True
        print("\n   Sections found:", flush=True)
        for section, found in sections.items():
            print(f"     {'✅' if found else '❌'} {section}", flush=True)
            if not found:
                all_sections = False

        # Check for full pass (all 8 sections)
        if all_sections and len(sections) >= 8:
            print(f"\n{'=' * 70}", flush=True)
            print(
                f"✅ TEST PASSED — Score: {score:.0%} — ALL {len(sections)} SECTIONS ✓ (attempt {attempt})",
                flush=True,
            )
            print(f"{'=' * 70}", flush=True)
            sys.exit(0)

        # Not all sections passed
        missing = [s for s, f in sections.items() if not f]
        print(f"\n   ⚠ Missing sections: {missing}", flush=True)
        if attempt < MAX_ATTEMPTS:
            print("   Retrying to get full rubric pass...", flush=True)

    # All attempts exhausted
    print(f"\n{'=' * 70}", flush=True)
    print(f"RESULT after {MAX_ATTEMPTS} attempts:", flush=True)
    print(f"  Best score: {best_score:.0%} (attempt {best_attempt})", flush=True)
    print("  Best sections:", flush=True)
    for section, found in best_sections.items():
        print(f"    {'✅' if found else '❌'} {section}", flush=True)

    if best_score >= 0.70:
        print(f"\n✅ TEST PASSED (best score {best_score:.0%})", flush=True)
        sys.exit(0)
    else:
        print(f"\n❌ TEST FAILED (best score {best_score:.0%})", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
