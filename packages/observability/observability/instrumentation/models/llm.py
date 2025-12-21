from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(default="user")
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None


class LLMRequest(BaseModel):
    system: Optional[str] = None
    operation: Optional[str] = None
    model: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    seed: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    streaming: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    provider_params: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    system: Optional[str] = None
    operation: Optional[str] = None
    model: Optional[str] = None
    content: Optional[str] = None
    role: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
