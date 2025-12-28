"""
Run all LTM tests in sequence.

This script runs all test examples to verify the LTM implementation.
"""

import asyncio
from pathlib import Path
import subprocess
import sys


def run_test(test_file: str) -> bool:
    """Run a single test file and return True if it passes."""
    print(f"\n{'=' * 70}")
    print(f"Running: {test_file}")
    print("=" * 70)

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=False,
            text=True,
            timeout=300,  # 5 minute timeout per test
        )
        if result.returncode == 0:
            print(f"✅ {test_file} PASSED")
            return True
        else:
            print(f"❌ {test_file} FAILED (exit code: {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  {test_file} TIMED OUT")
        return False
    except Exception as e:
        print(f"❌ {test_file} ERROR: {e}")
        return False


async def main():
    """Run all LTM tests."""
    print("\n" + "🧪 " * 25)
    print("  RUNNING ALL LTM TESTS")
    print("🧪 " * 25 + "\n")

    # Get the directory where this script is located
    test_dir = Path(__file__).parent

    # List of test files in order
    test_files = [
        "01_basic_facts.py",
        "02_fact_extraction.py",
        "03_memory_scoping.py",
        "04_integration_with_agent.py",
        "05_comprehensive_test.py",
        "06_advanced_runtime_access.py",
        "07_real_world_fitness_coach.py",
        "08_edge_cases_and_error_handling.py",
        "09_travel_planning_assistant.py",
    ]

    results = []
    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists():
            passed = run_test(str(test_path))
            results.append((test_file, passed))
        else:
            print(f"⚠️  {test_file} NOT FOUND")
            results.append((test_file, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_file, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {status}: {test_file}")

    print("\n" + "=" * 70)
    print(f"Total: {passed_count}/{total_count} tests passed")
    print("=" * 70)

    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
