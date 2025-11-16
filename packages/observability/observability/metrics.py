"""
Prometheus-based metrics collection for Astra.

This module provides metrics collection for agent performance, model usage,
tool execution, and cost tracking. Uses prometheus_client for metrics
with console output for MVP (easily extensible to Prometheus server).

Responsibilities:
- Track agent run counts, latencies, and success rates
- Monitor model token usage, costs, and time-to-first-token
- Record tool execution metrics and error rates
- Provide cost calculation utilities for different model providers
"""

import time
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.exposition import write_to_textfile


class MetricsRecorder:
    """
    Prometheus-based metrics recorder for Astra observability.
    
    Collects and exposes metrics for agent performance, model usage,
    tool execution, and cost tracking.
    """
    
    
    def __init__(self, service_name: str = "astra", registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics recorder with Prometheus collectors.

        Args:
            service_name (str, optional): Service name for metric labels
            registry (Optional[CollectorRegistry], optional): Custom registry (uses default if None)
        """
        
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        
        # Total number of agent runs
        self.agent_runs_total = Counter(
            'astra_agent_runs_total',
            'Total number of agent runs',
            ['agent_id', 'status'],
            registry=self.registry
        )
        
        # Agent run duration
        self.agent_run_duration = Histogram(
            'astra_agent_run_duration_seconds',
            'Agent run duration in seconds',
            ['agent_id'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.model_requests_total = Counter(
            'astra_model_requests_total',
            'Total number of model requests',
            ['model_name', 'provider', 'status'],
            registry=self.registry
        )
        
        self.model_tokens_total = Counter(
            'astra_model_tokens_total',
            'Total tokens processed by models',
            ['model_name', 'provider', 'token_type'],
            registry=self.registry
        )
        
        self.model_cost_total = Counter(
            'astra_model_cost_usd_total',
            'Total cost in USD for model usage',
            ['model_name', 'provider'],
            registry=self.registry
        )
        
        self.model_ttft = Histogram(
            'astra_model_ttft_seconds',
            'Time to first token from model',
            ['model_name', 'provider'],
            buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.tool_calls_total = Counter(
            'astra_tool_calls_total',
            'Total number of tool calls',
            ['tool_name', 'status'],
            registry=self.registry
        )
        
        self.tool_duration = Histogram(
            'astra_tool_duration_seconds',
            'Tool execution duration in seconds',
            ['tool_name'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
            registry=self.registry
        )
        
        self.memory_usage_bytes = Gauge(
            'astra_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
        
        
    def record_agent_run(
        self, 
        agent_id: str,
        duration_seconds: float,
        status: str = "success",
    ) -> None: 
        """
        Record metrics for an agent run.
        
        Args: 
            agent_id: Unique identifier for the agent
            duration_seconds: Total execution time in seconds
            status: Run status ("success", "error", "timeout")
        """
        
        self.agent_runs_total.labels(
            agent_id=agent_id,
            status=status,
        ).inc()
        
        self.agent_run_duration.labels(
            agent_id=agent_id
        ).observe(duration_seconds)
        
        
    def record_model_usage(
        self, 
        model_name: str,
        provider: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        ttft_seconds: Optional[float] = None,
        status: str = "success",
    ) -> None:
        """
        Record metrics for model usage.
        """
        
        self.model_requests_total.labels(
            model_name=model_name,
            provider=provider,
            status=status,
        ).inc()
        
        self.model_tokens_total.labels(
            model_name=model_name,
            provider=provider,
            token_type="input",
        ).inc(tokens_input)
        
        self.model_tokens_total.labels(
            model_name=model_name,
            provider=provider,
            token_type="output",
        ).inc(tokens_output)
        
        self.model_ttft.labels(
            model_name=model_name,
            provider=provider,
        ).observe(ttft_seconds)
        
        self.model_cost_total.labels(
            model_name=model_name,
            provider=provider,
        ).inc(cost_usd)
        
        
    def record_tool_call(
        self,
        tool_name: str,
        duration_seconds: float,
        status: str = "success",
    ) -> None:
        """
        Record metrics for a tool call.
        """
        
        self.tool_calls_total.labels(
            tool_name=tool_name,
            status=status,
        ).inc()
        
        self.tool_duration.labels(
            tool_name=tool_name,
        ).observe(duration_seconds)
        
    def record_memory_usage(self, component: str, bytes_used: int) -> None:
        """
        Record metrics for memory usage.
        
        Args:
            component: Component name (e.g., "agent", "memory", "tools")
            bytes_used: Memory usage in bytes
        """
        
        self.memory_usage_bytes.labels(
            component=component,
        ).set(bytes_used)
        
        
    def calculate_model_cost(
        self,
        model_name: str, 
        provider: str,
        tokens_input: int,
        tokens_output: int
    ) -> float:
        """
        Calculate cost for model usage based on current pricing.
        
        Args:
            model_name: Name of the model
            provider: Model provider
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            
        Returns:
            Total cost in USD
        """
        
        
        model_name = "GPT-4"
        provider = "OpenAI"
        tokens_input = 100
        tokens_output = 50
        
        return 0.5 # TODO: Implement actual cost calculation from the provider APIs
    
    
    def get_metrics_text(self) -> str:
        """
        Get metrics in Prometheus text format.
        """
        
        return generate_latest(self.registry).decode('utf-8')
    
    
    def export_to_file(self, filepath: str) -> None:
        """
        Export metrics to a file in Prometheus format.
        """
        
        write_to_textfile(filepath, self.registry)
        
        
    def reset_metrics(self) -> None:
        """
        Reset all metrics (useful for testing).
        
        Note: This creates new collector instances.
        """
        
        self.__init__(self.service_name, self.registry)
        
        
class MetricsTimer:
    """
    Context manager for timing operations and recording metrics.
    
    Example:
        with MetricsTimer(metrics.record_agent_run, agent_id="my_agent"):
            # Agent run logic here
            pass
    """
    
    def __init__(self, record_func, *args, **kwargs):
        """
        Initialize MetricsTimer with a recording function and arguments.

        Args:
            record_func: Function to record metrics
            *args: Positional arguments for the recording function
            **kwargs: Keyword arguments for the recording function
        """
        
        self.record_func = record_func
        self.kwargs = kwargs
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_value, traceback):
        if self.start_time is not None:
            duration  = time.perf_counter() - self.start_time
            status = "error" if exc_type is not None else "success"
            self.record_func(**self.kwargs, duration_seconds = duration, status = status)