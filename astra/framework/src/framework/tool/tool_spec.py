"""
Tool Specification for Astra Framework.

Declarative tool specification with 3-layer architecture:
- ToolSpec: Declarative specification (source of truth)
- bind_tool: Validates and builds runtime Tool
- Tool: Runtime object used by agents

The ToolSpec provides all the details needed to create Python stubs for LLM code generation.
By capturing tool metadata in a structured format, we enable the LLM to make better decisions about when and how to use each tool.

Current Implementation:
    - name: Tool identifier
    - description: High-level description
    - input_schema: Pydantic model for input validation
    - output_schema: Pydantic model for output structure
    - examples: Example input/output pairs for few-shot learning

Future Extensions (to be implemented): @TODO HeeManSu
    - version: Tool version for backward compatibility
    - when_to_use: List of scenarios where this tool is appropriate
    - when_not_to_use: List of scenarios to avoid this tool
    - constraints: Runtime constraints (e.g., "Date range <= 90 days")
    - guarantees: What the tool promises (e.g., "Always returns sorted results")
    - failure_modes: Known failure scenarios
    - edge_cases: Edge cases to be aware of
    - idempotent: Whether repeated calls with same input produce same result
    - side_effects: Whether the tool modifies external state
    - latency_ms: Expected latency hint
    - cost_hint: Computational/API cost indicator (low/medium/high)
    - preferred_for: Scenarios where this tool is the best choice
    - not_suitable_for: Scenarios where alternatives are better
    - tags: Categorization tags
    - category: Primary category
    - notes: Additional human-readable notes

Example Generated Stub (with future extensions):
    ```python
    def get_campaign_metrics(input: CampaignMetricsInput) -> list[CampaignMetricsOutput]:
        '''
        Fetch performance metrics for Amazon Ads campaigns.

        WHEN TO USE:
        - User asks about campaign performance, ACOS, ROAS
        - Need aggregated metrics across campaigns

        WHEN NOT TO USE:
        - Real-time data needed (use get_live_metrics instead)
        - Individual ad-level data required

        CONSTRAINTS:
        - Date range <= 90 days
        - Authenticated store only
        - Maximum 100 campaigns per request

        GUARANTEES:
        - Results always sorted by spend descending
        - All monetary values in USD

        FAILURE MODES:
        - Invalid store_id → returns empty list
        - No data available → returns empty list
        - API rate limit → raises RateLimitError

        COST: Medium
        IDEMPOTENT: Yes
        LATENCY: ~500ms

        Example:
            input = CampaignMetricsInput(
                store_id="store_123",
                start_date=date(2024, 9, 1),
                end_date=date(2024, 9, 30),
                campaign_type="sp"
            )
            result = get_campaign_metrics(input)
        '''
        ...
    ```

Current Usage:
    ```python
    from framework.tool import ToolSpec, bind_tool
    from pydantic import BaseModel, Field


    class MyInput(BaseModel):
        query: str = Field(description="Search query")


    class MyOutput(BaseModel):
        results: list[str] = Field(description="Search results")


    MY_TOOL_SPEC = ToolSpec(
        name="search",
        description="Search for information",
        input_schema=MyInput,
        output_schema=MyOutput,
        examples=[{"input": {"query": "python"}, "output": {"results": [...]}}],
    )


    @bind_tool(MY_TOOL_SPEC)
    async def search(input: MyInput) -> MyOutput:
        '''Implementation with rich metadata in docstring'''
        return MyOutput(results=[...])
    ```
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """
    Declarative specification for a tool.

    This is the single source of truth for tool metadata.
    All rich context (constraints, notes, usage guidance) should be in the
    implementation function's docstring until future fields are implemented.

    Current fields capture the essential information needed for:
    - Type validation (input/output models)
    - LLM understanding (description)
    - Few-shot learning (examples)

    Future fields will provide even richer context for LLM code generation,
    including usage guidance, constraints, failure modes, and more.
    """

    name: str = Field(description="Tool name (snake_case)")
    description: str = Field(description="High-level tool description")
    input_schema: type[BaseModel] = Field(description="Pydantic input schema")
    output_schema: type[BaseModel] = Field(description="Pydantic output schema")
    examples: list[dict] = Field(
        default_factory=list, description="Example input/output pairs for few-shot learning"
    )

    # Allow arbitrary types for Pydantic models
    model_config = {"arbitrary_types_allowed": True}
