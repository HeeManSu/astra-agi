from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(default="user")
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_tokens: int | None = None


class LLMRequest(BaseModel):
    system: str | None = None
    operation: str | None = None
    model: str | None = None
    messages: list[Message] = Field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    top_k: int | None = None
    seed: int | None = None
    stop_sequences: list[str] | None = None
    streaming: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider_params: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    system: str | None = None
    operation: str | None = None
    model: str | None = None
    content: str | None = None
    role: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
