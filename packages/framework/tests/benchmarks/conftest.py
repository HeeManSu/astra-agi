"""
Pytest configuration for benchmark tests.
"""

import pytest


@pytest.fixture
def benchmark_config():
    """
    Benchmark configuration for consistent testing.

    Returns:
        dict: Configuration for pytest-benchmark
    """
    return {
        "min_rounds": 100,  # Minimum number of rounds to run
        "warmup": True,  # Warmup before measuring
        "timer": "perf_counter",  # Use high-precision timer
    }
