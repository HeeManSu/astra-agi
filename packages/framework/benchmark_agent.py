"""
Benchmark script to measure Agent instantiation time and memory footprint.

Compares Astra Framework Agent performance with Agno's claims:
- Agno: ~3μs instantiation, ~6.6KiB memory
- Measures: Astra Agent instantiation time and memory usage
"""
import time
import statistics
import sys
import os
from typing import List
import tracemalloc
import gc

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Try to import memory profiling tools
try:
    from pympler import asizeof
    HAS_PYMPLER = True
except ImportError:
    HAS_PYMPLER = False
    print("Note: pympler not installed. Using sys.getsizeof (less accurate).")
    print("Install with: pip install pympler")


def measure_instantiation_time(num_runs: int = 10000) -> dict:
    """
    Measure Agent instantiation time over multiple runs.
    
    Args:
        num_runs: Number of iterations to run
        
    Returns:
        Dictionary with timing statistics
    """
    from framework import Agent
    
    times: List[float] = []
    
    # Warmup runs
    for _ in range(100):
        Agent(
            name='test-agent',
            instructions='Test instructions',
            model={'provider': 'openai', 'model': 'gpt-4'}
        )
    
    gc.collect()  # Force garbage collection
    
    # Actual measurement
    for _ in range(num_runs):
        start = time.perf_counter_ns()  # Nanosecond precision
        agent = Agent(
            name='test-agent',
            instructions='Test instructions',
            model={'provider': 'openai', 'model': 'gpt-4'}
        )
        end = time.perf_counter_ns()
        times.append((end - start) / 1000)  # Convert to microseconds
        del agent  # Explicit cleanup
    
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'min': min(times),
        'max': max(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'runs': num_runs,
        'unit': 'μs'
    }


def measure_memory_footprint(num_samples: int = 100) -> dict:
    """
    Measure Agent memory footprint.
    
    Args:
        num_samples: Number of agent instances to measure
        
    Returns:
        Dictionary with memory statistics
    """
    from framework import Agent
    
    # Clear any existing allocations
    gc.collect()
    
    if HAS_PYMPLER:
        # Use pympler for accurate memory measurement
        agents = []
        sizes = []
        
        for _ in range(num_samples):
            agent = Agent(
                name='test-agent',
                instructions='Test instructions',
                model={'provider': 'openai', 'model': 'gpt-4'},
                tools=[]
            )
            agents.append(agent)
            size = asizeof.asizeof(agent)
            sizes.append(size)
        
        # Cleanup
        del agents
        gc.collect()
        
        return {
            'mean': statistics.mean(sizes),
            'median': statistics.median(sizes),
            'min': min(sizes),
            'max': max(sizes),
            'stdev': statistics.stdev(sizes) if len(sizes) > 1 else 0,
            'samples': num_samples,
            'unit': 'bytes',
            'mean_kib': statistics.mean(sizes) / 1024,
            'method': 'pympler.asizeof'
        }
    else:
        # Fallback to sys.getsizeof (less accurate, doesn't include referenced objects)
        agents = []
        sizes = []
        
        for _ in range(num_samples):
            agent = Agent(
                name='test-agent',
                instructions='Test instructions',
                model={'provider': 'openai', 'model': 'gpt-4'},
                tools=[]
            )
            agents.append(agent)
            # sys.getsizeof only measures the object itself, not referenced objects
            size = sys.getsizeof(agent)
            # Try to estimate total size by summing attributes
            size += sys.getsizeof(agent.name) if hasattr(agent, 'name') else 0
            size += sys.getsizeof(agent.id) if hasattr(agent, 'id') else 0
            size += sys.getsizeof(agent.instructions) if hasattr(agent, 'instructions') else 0
            size += sys.getsizeof(agent.model) if hasattr(agent, 'model') else 0
            sizes.append(size)
        
        del agents
        gc.collect()
        
        return {
            'mean': statistics.mean(sizes),
            'median': statistics.median(sizes),
            'min': min(sizes),
            'max': max(sizes),
            'stdev': statistics.stdev(sizes) if len(sizes) > 1 else 0,
            'samples': num_samples,
            'unit': 'bytes',
            'mean_kib': statistics.mean(sizes) / 1024,
            'method': 'sys.getsizeof (approximate)',
            'note': 'This is an underestimate - does not include all referenced objects'
        }


def measure_memory_with_tracemalloc() -> dict:
    """
    Measure memory using Python's tracemalloc (more accurate than sys.getsizeof).
    
    Returns:
        Dictionary with memory statistics
    """
    from framework import Agent
    
    gc.collect()
    tracemalloc.start()
    
    # Snapshot before
    snapshot_before = tracemalloc.take_snapshot()
    
    # Create agent
    agent = Agent(
        name='test-agent',
        instructions='Test instructions',
        model={'provider': 'openai', 'model': 'gpt-4'},
        tools=[]
    )
    
    # Snapshot after
    snapshot_after = tracemalloc.take_snapshot()
    
    # Calculate difference
    top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
    
    total_size = sum(stat.size_diff for stat in top_stats)
    
    del agent
    gc.collect()
    tracemalloc.stop()
    
    return {
        'size_bytes': total_size,
        'size_kib': total_size / 1024,
        'method': 'tracemalloc',
        'unit': 'bytes'
    }


def print_results(time_stats: dict, memory_stats: dict, tracemalloc_stats: dict = None):
    """Print benchmark results in a formatted way."""
    print("\n" + "="*70)
    print("ASTRA FRAMEWORK - AGENT PERFORMANCE BENCHMARK")
    print("="*70)
    
    print("\n📊 INSTANTIATION TIME:")
    print(f"  Mean:     {time_stats['mean']:.3f} {time_stats['unit']}")
    print(f"  Median:    {time_stats['median']:.3f} {time_stats['unit']}")
    print(f"  Min:       {time_stats['min']:.3f} {time_stats['unit']}")
    print(f"  Max:       {time_stats['max']:.3f} {time_stats['unit']}")
    print(f"  Std Dev:   {time_stats['stdev']:.3f} {time_stats['unit']}")
    print(f"  Runs:      {time_stats['runs']:,}")
    
    print("\n💾 MEMORY FOOTPRINT:")
    print(f"  Mean:     {memory_stats['mean']:.2f} {memory_stats['unit']} ({memory_stats['mean_kib']:.3f} KiB)")
    print(f"  Median:   {memory_stats['median']:.2f} {memory_stats['unit']} ({memory_stats['median']/1024:.3f} KiB)")
    print(f"  Min:      {memory_stats['min']:.2f} {memory_stats['unit']} ({memory_stats['min']/1024:.3f} KiB)")
    print(f"  Max:      {memory_stats['max']:.2f} {memory_stats['unit']} ({memory_stats['max']/1024:.3f} KiB)")
    print(f"  Std Dev:  {memory_stats['stdev']:.2f} {memory_stats['unit']}")
    print(f"  Method:   {memory_stats['method']}")
    if 'note' in memory_stats:
        print(f"  Note:     {memory_stats['note']}")
    
    if tracemalloc_stats:
        print(f"\n  Tracemalloc: {tracemalloc_stats['size_bytes']:.2f} bytes ({tracemalloc_stats['size_kib']:.3f} KiB)")
    
    print("\n📈 COMPARISON WITH AGNO:")
    print(f"  Agno Claims:")
    print(f"    - Instantiation: ~3μs")
    print(f"    - Memory: ~6.6 KiB")
    print(f"\n  Astra Framework:")
    print(f"    - Instantiation: {time_stats['mean']:.3f}μs ({time_stats['mean']/3:.1f}x {'slower' if time_stats['mean'] > 3 else 'faster'} than Agno)")
    print(f"    - Memory: {memory_stats['mean_kib']:.3f} KiB ({memory_stats['mean_kib']/6.6:.1f}x {'more' if memory_stats['mean_kib'] > 6.6 else 'less'} than Agno)")
    
    print("\n" + "="*70 + "\n")


def main():
    """Run all benchmarks."""
    print("Running Astra Framework Agent benchmarks...")
    print("This may take a few moments...\n")
    
    # Measure instantiation time
    print("⏱️  Measuring instantiation time...")
    time_stats = measure_instantiation_time(num_runs=10000)
    
    # Measure memory footprint
    print("💾 Measuring memory footprint...")
    memory_stats = measure_memory_footprint(num_samples=100)
    
    # Try tracemalloc for additional accuracy
    tracemalloc_stats = None
    try:
        print("🔍 Measuring with tracemalloc...")
        tracemalloc_stats = measure_memory_with_tracemalloc()
    except Exception as e:
        print(f"   Tracemalloc measurement failed: {e}")
    
    # Print results
    print_results(time_stats, memory_stats, tracemalloc_stats)


if __name__ == "__main__":
    main()

