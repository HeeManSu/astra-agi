from pydantic import BaseModel, Field


class AgentMemory(BaseModel):
    """Configuration for Agent's short-term memory."""

    # Chat History (Context Window)
    add_history_to_messages: bool = Field(
        default=True, description="Add chat history to model messages"
    )
    num_history_responses: int = Field(
        default=10, description="Number of recent messages to keep in context"
    )

    # Summarization
    create_session_summary: bool = Field(
        default=False, description="Enable summarization of older messages"
    )

    summary_prompt: str = Field(
        default="Summarize the following conversation concisely, retaining key facts and decisions.",
        description="Prompt used for generating summaries",
    )
