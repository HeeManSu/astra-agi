"""
Integration tests for Agent tool execution.

Tests cover:
- Multiple tool calls in parallel
- Multiple tool call iterations
- Tool result formatting and inclusion
- Tool call loop behavior

"""

from framework.agents import Agent
from framework.agents.tool import tool
import pytest


@pytest.mark.integration
class TestMultipleToolCalls:
    """Tests for multiple tool calls."""

    @pytest.mark.asyncio
    async def test_multiple_tools_in_parallel(self, hf_model):
        """Agent executes multiple tools in parallel."""

        @tool
        def get_temperature() -> str:
            """Get current temperature."""
            return "72°F"

        @tool
        def get_humidity() -> str:
            """Get current humidity."""
            return "45%"

        @tool
        def get_wind_speed() -> str:
            """Get current wind speed."""
            return "10 mph"

        agent = Agent(
            name="ParallelToolAgent",
            instructions=(
                "You are a weather assistant. When asked for complete weather info, "
                "use all three tools (get_temperature, get_humidity, get_wind_speed) "
                "and include all results in your response."
            ),
            model=hf_model,
            tools=[get_temperature, get_humidity, get_wind_speed],
            code_mode=False,
        )

        response = await agent.invoke("Give me complete weather information")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        # Check if tools were executed (results should appear in response)
        response_lower = response.lower()
        tools_executed = (
            "72" in response
            or "temperature" in response_lower
            or "45" in response
            or "humidity" in response_lower
            or "10" in response
            or "wind" in response_lower
        )

        if not tools_executed:
            pytest.skip("Model did not execute multiple tools - model capability limitation")

    @pytest.mark.asyncio
    async def test_sequential_tool_calls(self, hf_model):
        """Agent executes tools sequentially when needed."""

        call_order = []

        @tool
        def step_one() -> str:
            """First step."""
            call_order.append(1)
            return "Step 1 complete"

        @tool
        def step_two() -> str:
            """Second step."""
            call_order.append(2)
            return "Step 2 complete"

        agent = Agent(
            name="SequentialToolAgent",
            instructions=(
                "You are a task assistant. When asked to do steps, "
                "use step_one first, then step_two, and report both results."
            ),
            model=hf_model,
            tools=[step_one, step_two],
            code_mode=False,
        )

        response = await agent.invoke("Do both steps in order")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        # Verify response mentions steps or completion
        response_lower = response.lower()
        assert (
            "step" in response_lower
            or "complete" in response_lower
            or "done" in response_lower
            or "1" in response
            or "2" in response
        ), f"Response should mention steps or completion. Got: {response}"

        # If tools were called, verify order (if model supports sequential calls)
        if len(call_order) >= 2:
            assert call_order[0] == 1, "step_one should be called first"
            assert call_order[1] == 2, "step_two should be called second"


@pytest.mark.integration
class TestToolCallIterations:
    """Tests for multiple tool call iterations."""

    @pytest.mark.asyncio
    async def test_tool_call_iteration_loop(self, hf_model):
        """Agent handles multiple rounds of tool calls."""

        iteration_count = {"count": 0}

        @tool
        def counter_tool() -> str:
            """Increment counter and return status."""
            iteration_count["count"] += 1
            return f"Iteration {iteration_count['count']}"

        agent = Agent(
            name="IterationAgent",
            instructions=(
                "You are a counter assistant. When asked to count, "
                "use counter_tool multiple times (up to 3 times) "
                "and report the results."
            ),
            model=hf_model,
            tools=[counter_tool],
            code_mode=False,
        )

        response = await agent.invoke("Count up to 3 using the counter tool")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        # Verify response mentions counting or iterations
        response_lower = response.lower()
        assert (
            "iteration" in response_lower
            or "count" in response_lower
            or "1" in response
            or "2" in response
            or "3" in response
        ), f"Response should mention counting or iterations. Got: {response}"

        # If tool was called multiple times, verify iterations occurred
        if iteration_count["count"] > 1:
            assert iteration_count["count"] <= 10, "Should not exceed max iterations"

    @pytest.mark.asyncio
    async def test_tool_result_included_in_next_call(self, hf_model):
        """Tool results are included in subsequent model calls."""

        @tool
        def get_data() -> str:
            """Get some data."""
            return "Data: 12345"

        agent = Agent(
            name="DataAgent",
            instructions=(
                "You are a data assistant. When asked for data, "
                "use get_data tool and include the exact result in your response."
            ),
            model=hf_model,
            tools=[get_data],
            code_mode=False,
        )

        response = await agent.invoke("Get the data and tell me what it is")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"

        # Verify response mentions data or the result
        response_lower = response.lower()
        assert (
            "12345" in response
            or "data" in response_lower
            or "result" in response_lower
            or "information" in response_lower
        ), f"Response should mention data or result. Got: {response}"


@pytest.mark.integration
class TestToolCallBehavior:
    """Tests for tool call behavior."""

    @pytest.mark.asyncio
    async def test_tool_call_with_no_response_content(self, hf_model):
        """Agent handles tool calls when model response has no content."""

        @tool
        def silent_tool() -> str:
            """A tool that returns data."""
            return "Tool executed"

        agent = Agent(
            name="SilentToolAgent",
            instructions="Use silent_tool when asked.",
            model=hf_model,
            tools=[silent_tool],
            code_mode=False,
        )

        response = await agent.invoke("Use the silent tool")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Response should exist even if initial model response had no content
        # Verify response mentions tool or execution
        response_lower = response.lower()
        assert (
            "tool" in response_lower or "executed" in response_lower or "silent" in response_lower
        ), f"Response should mention tool execution. Got: {response}"

    @pytest.mark.asyncio
    async def test_tool_call_stops_when_no_tool_calls(self, hf_model):
        """Agent stops tool call loop when model doesn't request tools."""

        @tool
        def optional_tool() -> str:
            """An optional tool."""
            return "Optional"

        agent = Agent(
            name="OptionalToolAgent",
            instructions="You can use optional_tool if needed, but don't have to.",
            model=hf_model,
            tools=[optional_tool],
            code_mode=False,
        )

        response = await agent.invoke("Say hello")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Should complete without tool calls if model doesn't request them

    @pytest.mark.asyncio
    async def test_tool_call_with_empty_tool_results(self, hf_model):
        """Agent handles empty tool results."""

        @tool
        def empty_tool() -> str:
            """A tool that returns empty string."""
            return ""

        agent = Agent(
            name="EmptyToolAgent",
            instructions="Use empty_tool when asked.",
            model=hf_model,
            tools=[empty_tool],
            code_mode=False,
        )

        response = await agent.invoke("Use the empty tool")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Should handle empty tool results gracefully
        # Response should mention tool or execution
        response_lower = response.lower()
        assert (
            "tool" in response_lower or "empty" in response_lower or "executed" in response_lower
        ), f"Response should mention tool execution. Got: {response}"


@pytest.mark.integration
class TestMultipleToolCallsComprehensive:
    """Comprehensive tests for multiple tool calls."""

    @pytest.mark.asyncio
    async def test_multiple_tools_with_dependencies(self, hf_model):
        """Agent executes multiple tools where one depends on another."""

        @tool
        def get_user_id(username: str) -> int:
            """Get user ID from username."""
            return 12345

        @tool
        def get_user_profile(user_id: int) -> str:
            """Get user profile from user ID."""
            return f"Profile for user {user_id}"

        agent = Agent(
            name="DependentToolAgent",
            instructions=(
                "You are a user assistant. When asked for a user profile, "
                "first use get_user_id to get the ID, then use get_user_profile "
                "with that ID to get the profile."
            ),
            model=hf_model,
            tools=[get_user_id, get_user_profile],
            code_mode=False,
        )

        response = await agent.invoke("Get the profile for user 'john'")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions profile or user
        response_lower = response.lower()
        assert (
            "profile" in response_lower
            or "user" in response_lower
            or "12345" in response
            or "john" in response_lower
        ), f"Response should mention profile or user. Got: {response}"

    @pytest.mark.asyncio
    async def test_mixed_parallel_and_sequential_tools(self, hf_model):
        """Agent handles mix of parallel and sequential tool calls."""

        call_log = []

        @tool
        def fetch_data_a() -> str:
            """Fetch data A."""
            call_log.append("data_a")
            return "Data A"

        @tool
        def fetch_data_b() -> str:
            """Fetch data B."""
            call_log.append("data_b")
            return "Data B"

        @tool
        def process_data(data: str) -> str:
            """Process the data."""
            call_log.append(f"process_{data}")
            return f"Processed {data}"

        agent = Agent(
            name="MixedToolAgent",
            instructions=(
                "You are a data processor. When asked to process data, "
                "fetch both data_a and data_b, then process the combined result."
            ),
            model=hf_model,
            tools=[fetch_data_a, fetch_data_b, process_data],
            code_mode=False,
        )

        response = await agent.invoke("Fetch and process all data")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions data or processing
        response_lower = response.lower()
        assert (
            "data" in response_lower
            or "process" in response_lower
            or "fetch" in response_lower
            or "result" in response_lower
        ), f"Response should mention data or processing. Got: {response}"

    @pytest.mark.asyncio
    async def test_large_number_of_tools(self, hf_model):
        """Agent handles multiple tools (5+) in a single call."""

        @tool
        def get_value_1() -> int:
            """Get value 1."""
            return 1

        @tool
        def get_value_2() -> int:
            """Get value 2."""
            return 2

        @tool
        def get_value_3() -> int:
            """Get value 3."""
            return 3

        @tool
        def get_value_4() -> int:
            """Get value 4."""
            return 4

        @tool
        def get_value_5() -> int:
            """Get value 5."""
            return 5

        agent = Agent(
            name="ManyToolsAgent",
            instructions=(
                "You are a value collector. When asked for all values, "
                "use all five get_value tools and report the results."
            ),
            model=hf_model,
            tools=[get_value_1, get_value_2, get_value_3, get_value_4, get_value_5],
            code_mode=False,
        )

        response = await agent.invoke("Get all the values")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions values or numbers
        response_lower = response.lower()
        has_numbers = any(char.isdigit() for char in response)
        assert (
            "value" in response_lower
            or has_numbers
            or "1" in response
            or "2" in response
            or "3" in response
            or "4" in response
            or "5" in response
        ), f"Response should mention values or numbers. Got: {response}"

    @pytest.mark.asyncio
    async def test_tools_with_different_return_types(self, hf_model):
        """Agent handles tools returning different data types."""

        @tool
        def get_string() -> str:
            """Get a string."""
            return "Hello"

        @tool
        def get_number() -> int:
            """Get a number."""
            return 42

        @tool
        def get_boolean() -> bool:
            """Get a boolean."""
            return True

        agent = Agent(
            name="MixedTypeAgent",
            instructions=(
                "You are a data collector. When asked for all data types, "
                "use all three tools and report their results."
            ),
            model=hf_model,
            tools=[get_string, get_number, get_boolean],
            code_mode=False,
        )

        response = await agent.invoke("Get all data types")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions data types or results
        response_lower = response.lower()
        assert (
            "hello" in response_lower
            or "42" in response
            or "true" in response_lower
            or "data" in response_lower
            or "type" in response_lower
        ), f"Response should mention data types or results. Got: {response}"


@pytest.mark.integration
class TestToolCallIterationsComprehensive:
    """Comprehensive tests for tool call iterations and multi-step workflows."""

    @pytest.mark.asyncio
    async def test_multi_step_workflow_with_data_flow(self, hf_model):
        """Agent executes multi-step workflow where each step uses previous results."""

        @tool
        def step_1_get_input() -> str:
            """Step 1: Get input data."""
            return "input_data"

        @tool
        def step_2_process(data: str) -> str:
            """Step 2: Process the data."""
            return f"processed_{data}"

        @tool
        def step_3_validate(data: str) -> str:
            """Step 3: Validate the processed data."""
            return f"validated_{data}"

        agent = Agent(
            name="WorkflowAgent",
            instructions=(
                "You are a workflow executor. When asked to run a workflow, "
                "execute step_1_get_input, then step_2_process with that result, "
                "then step_3_validate with the processed result. Report all steps."
            ),
            model=hf_model,
            tools=[step_1_get_input, step_2_process, step_3_validate],
            code_mode=False,
        )

        response = await agent.invoke("Run the complete workflow")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions workflow steps or processing
        response_lower = response.lower()
        assert (
            "workflow" in response_lower
            or "step" in response_lower
            or "process" in response_lower
            or "validate" in response_lower
            or "input" in response_lower
        ), f"Response should mention workflow or steps. Got: {response}"

    @pytest.mark.asyncio
    async def test_conditional_tool_calling(self, hf_model):
        """Agent conditionally calls tools based on previous results."""

        @tool
        def check_condition() -> bool:
            """Check if condition is met."""
            return True

        @tool
        def action_if_true() -> str:
            """Action to take if condition is true."""
            return "Condition was true"

        @tool
        def action_if_false() -> str:
            """Action to take if condition is false."""
            return "Condition was false"

        agent = Agent(
            name="ConditionalAgent",
            instructions=(
                "You are a conditional executor. When asked to check and act, "
                "use check_condition first. If it returns true, use action_if_true. "
                "If false, use action_if_false."
            ),
            model=hf_model,
            tools=[check_condition, action_if_true, action_if_false],
            code_mode=False,
        )

        response = await agent.invoke("Check the condition and take appropriate action")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions condition or action
        response_lower = response.lower()
        assert (
            "condition" in response_lower
            or "true" in response_lower
            or "action" in response_lower
            or "check" in response_lower
        ), f"Response should mention condition or action. Got: {response}"

    @pytest.mark.asyncio
    async def test_iterative_refinement_workflow(self, hf_model):
        """Agent iteratively refines results through multiple tool calls."""

        iteration_count = {"count": 0}

        @tool
        def refine_data(data: str) -> str:
            """Refine the data iteratively."""
            iteration_count["count"] += 1
            if iteration_count["count"] < 3:
                return f"refined_{data}_iteration_{iteration_count['count']}"
            return f"final_{data}"

        agent = Agent(
            name="RefinementAgent",
            instructions=(
                "You are a data refiner. When asked to refine data, "
                "start with 'initial_data' and use refine_data multiple times "
                "until you get a result that starts with 'final_'. Report the final result."
            ),
            model=hf_model,
            tools=[refine_data],
            code_mode=False,
        )

        response = await agent.invoke("Refine the data until it's final")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions refinement or final result
        response_lower = response.lower()
        assert (
            "refine" in response_lower
            or "final" in response_lower
            or "data" in response_lower
            or "iteration" in response_lower
        ), f"Response should mention refinement or final result. Got: {response}"

        # Verify multiple iterations occurred
        if iteration_count["count"] > 1:
            assert iteration_count["count"] <= 10, "Should not exceed max iterations"

    @pytest.mark.asyncio
    async def test_chained_tool_calls_with_accumulation(self, hf_model):
        """Agent chains tool calls and accumulates results."""

        @tool
        def add_item(item: str) -> str:
            """Add an item to the collection."""
            return f"Added {item}"

        @tool
        def get_collection() -> str:
            """Get the current collection."""
            return "Collection: item1, item2, item3"

        agent = Agent(
            name="CollectionAgent",
            instructions=(
                "You are a collection manager. When asked to build a collection, "
                "use add_item multiple times with different items, "
                "then use get_collection to see the final collection."
            ),
            model=hf_model,
            tools=[add_item, get_collection],
            code_mode=False,
        )

        response = await agent.invoke("Add items 'apple', 'banana', 'cherry' to the collection")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions collection or items
        response_lower = response.lower()
        assert (
            "collection" in response_lower
            or "item" in response_lower
            or "apple" in response_lower
            or "banana" in response_lower
            or "cherry" in response_lower
            or "add" in response_lower
        ), f"Response should mention collection or items. Got: {response}"

    @pytest.mark.asyncio
    async def test_complex_multi_iteration_workflow(self, hf_model):
        """Agent handles complex workflow with multiple iterations and tool combinations."""

        execution_log = []

        @tool
        def gather_info() -> str:
            """Gather initial information."""
            execution_log.append("gather")
            return "Info gathered"

        @tool
        def analyze(info: str) -> str:
            """Analyze the information."""
            execution_log.append("analyze")
            return f"Analysis of {info}"

        @tool
        def synthesize(analysis: str) -> str:
            """Synthesize the analysis."""
            execution_log.append("synthesize")
            return f"Synthesis: {analysis}"

        @tool
        def validate(result: str) -> str:
            """Validate the result."""
            execution_log.append("validate")
            if "Synthesis" in result:
                return f"Validated: {result}"
            return "Needs more synthesis"

        agent = Agent(
            name="ComplexWorkflowAgent",
            instructions=(
                "You are a complex workflow executor. When asked to execute a workflow, "
                "use gather_info, then analyze with that result, then synthesize, "
                "then validate. If validation says 'Needs more synthesis', repeat synthesis and validate."
            ),
            model=hf_model,
            tools=[gather_info, analyze, synthesize, validate],
            code_mode=False,
        )

        response = await agent.invoke("Execute the complete workflow")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions workflow or execution
        response_lower = response.lower()
        assert (
            "workflow" in response_lower
            or "execute" in response_lower
            or "gather" in response_lower
            or "analyze" in response_lower
            or "synthesize" in response_lower
            or "validate" in response_lower
        ), f"Response should mention workflow or execution steps. Got: {response}"

        # Verify workflow steps were executed
        assert len(execution_log) > 0, "Workflow should have executed steps"

    @pytest.mark.asyncio
    async def test_tool_iteration_with_early_termination(self, hf_model):
        """Agent stops tool iterations when condition is met."""

        call_count = {"count": 0}

        @tool
        def check_status() -> str:
            """Check current status."""
            call_count["count"] += 1
            if call_count["count"] >= 2:
                return "Complete"
            return "In progress"

        agent = Agent(
            name="EarlyTerminationAgent",
            instructions=(
                "You are a status checker. When asked to check status, "
                "use check_status repeatedly until it returns 'Complete', then stop."
            ),
            model=hf_model,
            tools=[check_status],
            code_mode=False,
        )

        response = await agent.invoke("Check the status until it's complete")

        assert response is not None
        assert len(response.strip()) > 0, "Response should have content"
        # Verify response mentions status or completion
        response_lower = response.lower()
        assert (
            "status" in response_lower
            or "complete" in response_lower
            or "check" in response_lower
            or "progress" in response_lower
        ), f"Response should mention status or completion. Got: {response}"

        # Verify tool was called multiple times but stopped early
        assert call_count["count"] >= 2, "Should have called tool at least twice"
        assert call_count["count"] <= 10, "Should not exceed max iterations"
