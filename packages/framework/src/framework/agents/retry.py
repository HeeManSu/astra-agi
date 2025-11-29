import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class RetryableError(Exception):
    """Errors that should trigger retry."""


async def retry_with_backoff(func: Callable, config: RetryConfig, context: Any = None) -> Any:
    """
    Retry function with exponential backoff.

    Args:
        func: Async function to retry
        config: Retry configuration
        context: Optional context for logging

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries fail
    """

    last_exception: Exception | None = None

    for attempt in range(1, config.max_retries + 1):
        if context:
            context.attempt = attempt

        try:
            result = await func()
            return result

        except Exception as e:
            last_exception = e

            # Don't retry on last attempt
            if attempt == config.max_retries:
                break

            # Calculate delay
            delay = calculate_delay(attempt, config)

            # Log retry
            if context and hasattr(context, "observability") and context.observability:
                context.observability.logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay:.2f}s",
                    error=str(e),
                    attempt=attempt,
                )

            # Wait before retry
            await asyncio.sleep(delay)

    # All retries exhausted - last_exception should not be None here
    if last_exception is None:
        raise RuntimeError("Retry failed but no exception was captured")
    raise last_exception


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for exponential backoff."""

    delay = config.initial_delay * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd
    if config.jitter:
        import random

        delay = delay * (0.5 + random.random() * 0.5)

    return delay
