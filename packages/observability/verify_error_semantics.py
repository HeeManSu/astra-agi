import asyncio

from observability.client import Client
from observability.semantic import trace_tool


# Initialize Observability with Console Exporter to see output
client = Client(service_name="test-error-service", endpoint="console", enable_tracing=True)

class RetryableError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.retryable = True
        self.error_type = "transient_failure"
        self.stage = "data_fetch"

@trace_tool(name="flaky_tool")
async def flaky_func():
    print("Running flaky tool...")
    raise RetryableError("Something bad happened but it is retryable")

async def run_test():
    try:
        await flaky_func()
    except Exception:
        print("Caught expected exception")

if __name__ == "__main__":
    asyncio.run(run_test())
