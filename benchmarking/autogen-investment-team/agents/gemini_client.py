"""
Gemini ChatCompletionClient for AutoGen v0.4+.

AutoGen v0.4 ships built-in clients for OpenAI, Anthropic, Ollama, etc. — but
no native Gemini client. The `autogen-ext[gemini]` extra just pulls in
`google-genai` as a dep; it does not provide a class.

For the benchmark we need AutoGen calls to route through `google.genai`'s
`Models.generate_content` (sync) or `AsyncModels.generate_content` (async)
because that is the exact SDK boundary the harness's `DebugCounter`
patches — the same patch point Agno, CrewAI, and Astra hit. Routing through
the OpenAI-compatible Gemini endpoint would bypass the counter and report
zero calls.

This module implements `GeminiChatCompletionClient(ChatCompletionClient)`
that translates AutoGen's message + tool types into `google.genai`'s
Content / Tool types, dispatches via `google.genai`, and translates the
response back into an AutoGen `CreateResult`. Thinking is forced OFF via
ThinkingConfig.
"""

from __future__ import annotations

import json
from os import getenv
from typing import AsyncGenerator, Mapping, Optional, Sequence

from autogen_core import CancellationToken, FunctionCall
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    FinishReasons,
    FunctionExecutionResultMessage,
    LLMMessage,
    ModelFamily,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import Tool, ToolSchema
from google import genai
from google.genai import types as gtypes
from pydantic import BaseModel


def _strip_jsonschema(schema: dict | None) -> dict:
    """Gemini's function-declaration schema is a subset of JSON Schema.
    Drop fields it doesn't accept (additionalProperties, $defs, title, etc.)."""
    if not schema:
        return {"type": "object", "properties": {}}

    drop = {"additionalProperties", "$defs", "$schema", "title", "default"}

    def _clean(node):
        if isinstance(node, dict):
            return {k: _clean(v) for k, v in node.items() if k not in drop}
        if isinstance(node, list):
            return [_clean(x) for x in node]
        return node

    cleaned = _clean(schema)
    # Required minimum for Gemini: an "object" type with properties.
    if "type" not in cleaned:
        cleaned["type"] = "object"
    if cleaned.get("type") == "object" and "properties" not in cleaned:
        cleaned["properties"] = {}
    return cleaned


def _tool_schema(tool: Tool | ToolSchema) -> dict:
    """Coerce a Tool or ToolSchema into the dict shape we read from."""
    if isinstance(tool, dict):
        return tool
    return tool.schema  # autogen_core.tools.Tool exposes .schema


def _to_genai_tools(tools: Sequence[Tool | ToolSchema]) -> list[gtypes.Tool]:
    """Convert AutoGen tool schemas to a google.genai Tool[].

    google.genai allows multiple FunctionDeclarations on a single Tool.
    """
    if not tools:
        return []
    decls = []
    for t in tools:
        s = _tool_schema(t)
        params = _strip_jsonschema(s.get("parameters"))
        decls.append(
            gtypes.FunctionDeclaration(
                name=s["name"],
                description=s.get("description", "") or "",
                parameters=params,
            )
        )
    return [gtypes.Tool(function_declarations=decls)]


def _to_genai_contents(messages: Sequence[LLMMessage]) -> tuple[str, list[gtypes.Content]]:
    """Translate AutoGen messages → (system_instruction, contents[]).

    Gemini takes the system message via a top-level `system_instruction`
    parameter, not in the message list. SelectorGroupChat may emit multiple
    SystemMessages over a conversation — we concatenate them.
    """
    sys_parts: list[str] = []
    contents: list[gtypes.Content] = []

    for m in messages:
        if isinstance(m, SystemMessage):
            sys_parts.append(m.content if isinstance(m.content, str) else str(m.content))
            continue

        if isinstance(m, UserMessage):
            # m.content is str | list[str | Image]; benchmark is text-only.
            text = (
                m.content if isinstance(m.content, str) else " ".join(str(c) for c in m.content if isinstance(c, str))
            )
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part(text=text)]))
            continue

        if isinstance(m, AssistantMessage):
            # content is str | list[FunctionCall]
            if isinstance(m.content, str):
                contents.append(gtypes.Content(role="model", parts=[gtypes.Part(text=m.content)]))
            else:
                # list of FunctionCall
                parts: list[gtypes.Part] = []
                for fc in m.content:
                    try:
                        args = json.loads(fc.arguments) if isinstance(fc.arguments, str) else fc.arguments
                    except Exception:
                        args = {"raw_arguments": fc.arguments}
                    parts.append(gtypes.Part(function_call=gtypes.FunctionCall(name=fc.name, args=args or {})))
                contents.append(gtypes.Content(role="model", parts=parts))
            continue

        if isinstance(m, FunctionExecutionResultMessage):
            # m.content is list[FunctionExecutionResult]
            parts = []
            for fr in m.content:
                # function response can be any JSON; wrap strings into {"result": ...}.
                try:
                    response_obj = json.loads(fr.content) if isinstance(fr.content, str) else fr.content
                    if not isinstance(response_obj, dict):
                        response_obj = {"result": response_obj}
                except Exception:
                    response_obj = {"result": fr.content}
                parts.append(
                    gtypes.Part(
                        function_response=gtypes.FunctionResponse(name=fr.name or "tool", response=response_obj)
                    )
                )
            contents.append(gtypes.Content(role="user", parts=parts))
            continue

    return ("\n\n".join(sys_parts) if sys_parts else "", contents)


def _map_finish_reason(reason) -> FinishReasons:
    """google.genai FinishReason → AutoGen FinishReasons."""
    if reason is None:
        return "unknown"
    s = str(reason).upper()
    if "STOP" in s:
        return "stop"
    if "MAX_TOKENS" in s or "LENGTH" in s:
        return "length"
    if "SAFETY" in s:
        return "content_filter"
    if "FUNCTION" in s or "TOOL" in s:
        return "function_calls"
    return "unknown"


class GeminiChatCompletionClient(ChatCompletionClient):
    """AutoGen ChatCompletionClient that uses google.genai under the hood.

    All LLM calls route through `google.genai.Client.aio.models.generate_content`,
    which is the SDK boundary the benchmark's `DebugCounter` patches at the
    class level. So every AutoGen LLM call is counted automatically, the same
    way Agno / CrewAI / Astra are.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        *,
        temperature: float = 0.0,
        thinking_config: Optional[gtypes.ThinkingConfig] = None,
    ):
        self._model = model
        self._temperature = temperature
        self._thinking_config = thinking_config or gtypes.ThinkingConfig(thinking_budget=0, include_thoughts=False)

        api_key = getenv("GOOGLE_API_KEY") or getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is required")
        # Pass key explicitly so we don't depend on env-order quirks.
        self._client = genai.Client(api_key=api_key)

        self._total = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._last = RequestUsage(prompt_tokens=0, completion_tokens=0)

    # ---- abstract surface ----

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = (),
        tool_choice: Tool | str = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, object] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        system_instruction, contents = _to_genai_contents(messages)
        genai_tools = _to_genai_tools(tools)

        config = gtypes.GenerateContentConfig(
            temperature=self._temperature,
            thinking_config=self._thinking_config,
            system_instruction=system_instruction or None,
            tools=genai_tools or None,
        )

        if json_output is True:
            config.response_mime_type = "application/json"

        # Force tool use only if caller passed a specific Tool object as tool_choice.
        # AutoGen passes "auto" / "required" / "none" by default; map them to
        # google.genai's tool_config when appropriate.
        if tool_choice == "required" and genai_tools:
            config.tool_config = gtypes.ToolConfig(function_calling_config=gtypes.FunctionCallingConfig(mode="ANY"))
        elif tool_choice == "none":
            config.tool_config = gtypes.ToolConfig(function_calling_config=gtypes.FunctionCallingConfig(mode="NONE"))

        # Single SDK call — this hits the DebugCounter-patched method.
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )

        # Extract content & tool calls from the candidate.
        text_parts: list[str] = []
        function_calls: list[FunctionCall] = []
        finish = None

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            cand = candidates[0]
            finish = getattr(cand, "finish_reason", None)
            for part in getattr(cand.content, "parts", []) or []:
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    function_calls.append(
                        FunctionCall(
                            id=f"call_{len(function_calls)}",
                            name=fc.name,
                            arguments=json.dumps(dict(fc.args) if fc.args else {}),
                        )
                    )
                    continue
                t = getattr(part, "text", None)
                if t:
                    text_parts.append(t)

        # Usage from SDK.
        usage_md = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage_md, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage_md, "candidates_token_count", 0) or 0)
        usage = RequestUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        self._last = usage
        self._total = RequestUsage(
            prompt_tokens=self._total.prompt_tokens + prompt_tokens,
            completion_tokens=self._total.completion_tokens + completion_tokens,
        )

        if function_calls:
            content: str | list[FunctionCall] = function_calls
            finish_reason: FinishReasons = "function_calls"
        else:
            content = "".join(text_parts) if text_parts else ""
            finish_reason = _map_finish_reason(finish)

        return CreateResult(
            content=content,
            usage=usage,
            finish_reason=finish_reason,
            cached=False,
        )

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = (),
        tool_choice: Tool | str = "auto",
        json_output: Optional[bool | type[BaseModel]] = None,
        extra_create_args: Mapping[str, object] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator:
        # Streaming isn't required by SelectorGroupChat for the benchmark.
        # Delegate to create() and yield the final CreateResult.
        result = await self.create(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            json_output=json_output,
            extra_create_args=extra_create_args,
            cancellation_token=cancellation_token,
        )
        yield result

    def actual_usage(self) -> RequestUsage:
        return self._last

    def total_usage(self) -> RequestUsage:
        return self._total

    def count_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = ()) -> int:
        # Rough estimate — Gemini's count_tokens API would require another call.
        # Returning a coarse estimate is fine because AutoGen only uses this
        # for budget bookkeeping (we do not enforce a budget in this benchmark).
        sys_text, contents = _to_genai_contents(messages)
        total_chars = len(sys_text)
        for c in contents:
            for p in c.parts or []:
                if getattr(p, "text", None):
                    total_chars += len(p.text)
        return max(1, total_chars // 4)

    def remaining_tokens(self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = ()) -> int:
        # 1M-ish context window minus rough used estimate. Don't enforce.
        return 1_000_000 - self.count_tokens(messages, tools=tools)

    @property
    def model_info(self) -> ModelInfo:
        return ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family=ModelFamily.GEMINI_2_5_FLASH,
            structured_output=True,
            multiple_system_messages=False,
        )

    @property
    def capabilities(self):  # deprecated upstream; kept for ABC compliance
        return self.model_info

    async def close(self) -> None:
        # google.genai client has no async close; nothing to release.
        return None
