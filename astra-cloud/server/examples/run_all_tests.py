#!/usr/bin/env python3
"""Test runner for all runtime examples."""

from pathlib import Path
import subprocess
import sys


EXAMPLES_DIR = Path(__file__).parent
EXAMPLES = [
    "01_basic_agent.py",
    "02_background_job.py",
    "03_streaming.py",
    "04_agent_with_tools.py",
    "05_agent_properties.py",
    "06_rag_ingest.py",
    "07_rag_directory.py",
    "08_advanced_config.py",
]


def run_example(example_file: str) -> tuple[bool, str, str]:
    """Run a single example and return success status and output."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {example_file}")
    print(f"{'=' * 60}")

    cmd = [
        "uv",
        "run",
        "--package",
        "astra-runtime",
        "python",
        f"packages/runtime/examples/{example_file}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/Users/himanshu/Desktop/open-source/Astra",
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        if success:
            print("✅ PASSED")
            print("\nOutput (last 20 lines):")
            print("\n".join(output.split("\n")[-20:]))
        else:
            print(f"❌ FAILED (exit code: {result.returncode})")
            print("\nError output:")
            print(result.stderr[-1000:])

        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT (>60s)")
        return False, "", "Timeout after 60 seconds"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False, "", str(e)


def main():
    """Run all examples and report results."""
    print("\n" + "=" * 60)
    print("ASTRA RUNTIME - EXAMPLE TEST SUITE")
    print("=" * 60)

    results = {}
    for example in EXAMPLES:
        success, stdout, stderr = run_example(example)
        results[example] = {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
        }

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r["success"])
    failed = len(results) - passed

    for example, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} - {example}")

    print(f"\nTotal: {len(results)} | Passed: {passed} | Failed: {failed}")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
