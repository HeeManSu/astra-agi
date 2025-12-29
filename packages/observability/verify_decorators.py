import asyncio
import os
from observability.client import Client
from observability.semantic import trace_agent, trace_tool, trace_llm, trace_step, with_context
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry import trace

# Initialize Observability with Console Exporter to see output
client = Client(service_name="test-service", endpoint="console", enable_tracing=True)

@trace_tool(name="search_tool")
async def search(query: str):
    print(f"Searching for: {query}")
    return "Search Results"

@trace_llm(model="gpt-4", temperature=0.7)
async def generate_thought(prompt: str):
    print(f"Generating thought for: {prompt}")
    return "I should search for observability."

@trace_step(step_name="planning", step_type="reasoning")
async def plan_step():
    print("Planning...")
    thought = await generate_thought("How to implement tracing?")
    return thought

@trace_agent(name="TestAgent", agent_type="researcher")
@with_context(user_id="user_123", session_id="session_abc")
async def run_agent():
    print("Agent starting...")
    plan = await plan_step()
    result = await search(plan)
    print(f"Agent finished with: {result}")

if __name__ == "__main__":
    asyncio.run(run_agent())
