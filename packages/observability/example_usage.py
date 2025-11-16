"""
Example usage of the Astra Observability package.

This file demonstrates how to use the observability components
in a typical agent execution scenario.
"""

import asyncio
import time
from observability import init_observability


async def example_agent_run():
    """
    Example of how to use observability in an agent run.
    """
    # Initialize observability
    obs = init_observability(
        service_name="astra-example",
        environment="dev",
        log_level="INFO",
        enable_json_logs=True
    )
    
    agent_id = "example-agent"
    session_id = "session-123"
    request_id = "req-456"
    
    # Example 1: Using the trace decorator with composition pattern
    @obs.trace_agent_run(agent_id)
    async def run_agent():
        obs.logger.log_agent_start(
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id
        )
        
        # Simulate agent processing
        await asyncio.sleep(0.1)
        
        # Example model call
        await simulate_model_call(obs, agent_id, session_id, request_id)
        
        # Example tool call
        await simulate_tool_call(obs, agent_id, session_id, request_id)
        
        obs.logger.log_agent_complete(
            agent_id=agent_id,
            duration_ms=150,
            session_id=session_id,
            request_id=request_id
        )
        
        return "Agent completed successfully"
    
    # Run the agent
    start_time = time.perf_counter()
    try:
        result = await run_agent()
        duration = time.perf_counter() - start_time
        
        # Record metrics using composition pattern
        obs.metrics.record_agent_run(
            agent_id=agent_id,
            duration_seconds=duration,
            status="success",
            environment="dev"
        )
        
        obs.logger.info(f"Agent run completed: {result}", agent_id=agent_id)
        
    except Exception as e:
        duration = time.perf_counter() - start_time
        obs.metrics.record_agent_run(
            agent_id=agent_id,
            duration_seconds=duration,
            status="error",
            environment="dev"
        )
        obs.logger.error("Agent run failed", exception=e, agent_id=agent_id)
        raise
    
    # Print metrics for demo
    print("\n=== METRICS OUTPUT ===")
    print(obs.metrics.get_metrics_text())
    
    # Shutdown
    obs.shutdown()


async def simulate_model_call(obs, agent_id, session_id, request_id):
    """Simulate a model API call with observability."""
    
    @obs.trace_model_call("gpt-4", "openai")
    async def call_model():
        obs.logger.info(
            "Making model call",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            model="gpt-4"
        )
        
        # Simulate API call
        await asyncio.sleep(0.05)
        
        # Simulate response processing
        tokens_input = 100
        tokens_output = 50
        cost = obs.metrics.calculate_model_cost("gpt-4", "openai", tokens_input, tokens_output)
        
        # Record metrics and logs using composition pattern
        obs.metrics.record_model_usage(
            model_name="gpt-4",
            provider="openai",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            ttft_seconds=0.02,
            status="success",
            environment="dev"
        )
        
        obs.logger.log_model_call(
            model_name="gpt-4",
            provider="openai",
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_usd=cost,
            duration_ms=50,
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id
        )
        
        return "Model response"
    
    return await call_model()


async def simulate_tool_call(obs, agent_id, session_id, request_id):
    """Simulate a tool call with observability."""
    
    @obs.trace_tool_call("web_search")
    async def call_tool():
        obs.logger.info(
            "Calling tool",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id,
            tool="web_search"
        )
        
        # Simulate tool execution
        start_time = time.perf_counter()
        await asyncio.sleep(0.03)
        duration = time.perf_counter() - start_time
        
        # Record metrics and logs using composition pattern
        obs.metrics.record_tool_call(
            tool_name="web_search",
            duration_seconds=duration,
            status="success",
            environment="dev"
        )
        
        obs.logger.log_tool_call(
            tool_name="web_search",
            duration_ms=int(duration * 1000),
            status="success",
            agent_id=agent_id,
            session_id=session_id,
            request_id=request_id
        )
        
        return "Tool result"
    
    return await call_tool()


async def example_manual_tracing():
    """
    Example of manual span management (alternative to decorators).
    """
    obs = init_observability(service_name="astra-manual", environment="dev")
    
    # Manual span creation using composition pattern
    span = obs.tracer.start_span("manual.operation", {"operation": "data_processing"})
    
    try:
        obs.logger.info("Starting manual operation")
        
        # Add events to the span
        obs.tracer.add_event("processing.started", {"items": 100})
        
        # Simulate work
        await asyncio.sleep(0.02)
        
        # Set attributes
        obs.tracer.set_attribute("items.processed", 100)
        obs.tracer.set_attribute("processing.success", True)
        
        obs.tracer.add_event("processing.completed", {"duration_ms": 20})
        obs.logger.info("Manual operation completed")
        
    except Exception as e:
        obs.tracer.record_exception(e)
        obs.logger.error("Manual operation failed", exception=e)
        raise
    finally:
        # Span is automatically ended when it goes out of scope
        # but you can also end it manually if needed
        pass
    
    obs.shutdown()


def example_metrics_only():
    """
    Example of using just the metrics component.
    """
    from observability import MetricsRecorder, MetricsTimer
    
    metrics = MetricsRecorder("astra-metrics-only")
    
    # Record some metrics
    metrics.record_agent_run("test-agent", 1.5, "success", "dev")
    metrics.record_model_usage("gpt-4", "openai", 100, 50, 0.005, 0.02, "success", "dev")
    metrics.record_tool_call("calculator", 0.01, "success", "dev")
    
    # Use timer context manager
    with MetricsTimer(metrics.record_tool_call, tool_name="database", environment="dev"):
        time.sleep(0.05)  # Simulate work
    
    # Print metrics
    print("=== METRICS ONLY ===")
    print(metrics.get_metrics_text())


if __name__ == "__main__":
    print("=== Astra Observability Examples ===\n")
    
    print("1. Running full agent example...")
    asyncio.run(example_agent_run())
    
    print("\n2. Running manual tracing example...")
    asyncio.run(example_manual_tracing())
    
    print("\n3. Running metrics-only example...")
    example_metrics_only()
    
    print("\nAll examples completed!")
