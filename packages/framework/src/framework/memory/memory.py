from pydantic import BaseModel, Field


class AgentMemory(BaseModel):
    """
    Configuration for Agent's short-term memory (STM).

    Controls how conversation history is loaded and managed for the agent.
    """

    add_history_to_messages: bool = Field(
        default=True, description="Whether to add chat history to model messages"
    )
    num_history_responses: int = Field(
        default=10,
        description="Number of recent conversation turns to keep (deprecated: use window_size)",
    )

    token_limit: int | None = Field(
        default=None,
        description="Token limit for context window (primary). If None, uses window_size.",
    )
    window_size: int = Field(
        default=20,
        description="Message count limit (fallback when token_limit is None). Counts actual messages, not turns.",
    )
    summarize_overflow: bool = Field(
        default=True,
        description="Whether to summarize old messages when exceeding token/window limit",
    )
    include_system_messages: bool = Field(
        default=True,
        description="Whether to count system messages toward window_size limit",
    )
    summary_model: str | None = Field(
        default=None,
        description="Model ID for summarization (lighter/faster model). If None, uses agent's model.",
    )

    # Summarization Prompt
    summary_prompt: str = Field(
        default="Summarize the following conversation concisely, retaining key facts and decisions.",
        description="Prompt used for generating summaries",
    )
