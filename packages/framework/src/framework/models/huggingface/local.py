from collections.abc import AsyncIterator
import json
import logging
import re
import threading
import time
from typing import Any, ClassVar

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
    TextIteratorStreamer,
)

from framework.models.base import Model, ModelResponse


logger = logging.getLogger(__name__)


class HuggingFaceLocal(Model):
    """
    Local Hugging Face model provider using `transformers` library.
    Runs models locally on CPU/GPU with tool calling support.
    """

    # Common tool call patterns in model outputs
    TOOL_CALL_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # Hermes/NousResearch format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
        re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL),
        # Alternative format: [TOOL_CALL]{"name": "...", "arguments": {...}}[/TOOL_CALL]
        re.compile(r"\[TOOL_CALL\]\s*(\{.*?\})\s*\[/TOOL_CALL\]", re.DOTALL),
        # Function call format: {"function_call": {"name": "...", "arguments": "..."}}
        re.compile(r'\{"function_call":\s*(\{.*?\})\}', re.DOTALL),
        # Direct JSON object with name and arguments at end of response
        re.compile(r'```json\s*(\{"name":\s*"[^"]+",\s*"arguments":\s*\{.*?\}\})\s*```', re.DOTALL),
    ]

    def __init__(
        self,
        model_id: str,
        device: str | None = None,
        torch_dtype: Any | None = None,
        max_new_tokens: int = 1024,
        **kwargs: Any,
    ):
        """
        Initialize the local Hugging Face model.

        Args:
            model_id: Hugging Face model ID (e.g. "meta-llama/Llama-3.2-1B-Instruct")
            device: Device to run on ("cuda", "mps", "cpu", or "auto"). Defaults to auto-detect.
            torch_dtype: Torch data type (e.g. torch.bfloat16). Defaults to auto.
            max_new_tokens: Default max tokens to generate.
            **kwargs: Additional arguments passed to AutoModelForCausalLM.from_pretrained
        """
        super().__init__(model_id=model_id, api_key="local", **kwargs)
        self.device = device or self._detect_device()
        self.torch_dtype = torch_dtype or "auto"
        self.max_new_tokens = max_new_tokens
        self.model_kwargs = kwargs

        self._tokenizer: PreTrainedTokenizer | None = None
        self._model: PreTrainedModel | None = None

    def _detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _load_model(self) -> None:
        """Lazy load model and tokenizer."""
        if self._model is not None:
            return

        logger.info(f"Loading local model: {self.model_id} on {self.device}...")
        start = time.perf_counter()

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)

            # device_map="auto" usually works best with accelerate
            if self.device == "cpu":
                # CPU doesn't support device_map="auto" usually in same way, explicit is safer
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_id, dtype=self.torch_dtype, **self.model_kwargs
                )
                self._model.to(torch.device("cpu"))  # type: ignore
            else:
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    dtype=self.torch_dtype,
                    device_map="auto" if self.device != "mps" else None,
                    **self.model_kwargs,
                )
                if self.device == "mps" and not getattr(self._model, "is_loaded_in_8bit", False):
                    self._model.to(torch.device("mps"))  # type: ignore

            logger.info(f"Model loaded in {time.perf_counter() - start:.2f}s")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_id}: {e}")
            raise RuntimeError(f"Failed to load model {self.model_id}: {e}") from e

    def _format_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert Astra tool definitions to HuggingFace format.

        Astra format:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }

        HuggingFace format (for apply_chat_template):
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "...",
                "parameters": {...}
            }
        }

        The formats are compatible, but we normalize for safety.
        """
        hf_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                hf_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": func.get("name", ""),
                            "description": func.get("description", ""),
                            "parameters": func.get("parameters", {}),
                        },
                    }
                )
            else:
                # Pass through other tool types
                hf_tools.append(tool)
        return hf_tools

    def _parse_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """
        Parse tool calls from model output.

        Supports multiple formats:
        - Hermes: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
        - Mistral: [TOOL_CALL]...[/TOOL_CALL]
        - JSON code blocks with function call objects

        Returns a list of tool call dictionaries with:
        - id: Generated unique ID
        - type: "function"
        - function: {"name": "...", "arguments": {...}}
        """
        tool_calls: list[dict[str, Any]] = []

        # Collect all matches first
        all_matches: list[str] = []
        for pattern in self.TOOL_CALL_PATTERNS:
            all_matches.extend(pattern.findall(content))

        # Parse matches using helper (avoids try-except in loop - PERF203)
        for match in all_matches:
            parsed = self._try_parse_tool_match(match, len(tool_calls))
            if parsed:
                tool_calls.append(parsed)

        return tool_calls

    def _try_parse_tool_match(self, match: str, idx: int) -> dict[str, Any] | None:
        """Try to parse a single tool call match. Returns None on failure."""
        try:
            parsed = json.loads(match)

            # Handle different JSON structures
            if "name" in parsed and "arguments" in parsed:
                # Direct format: {"name": "...", "arguments": {...}}
                return {
                    "id": f"call_{idx}_{int(time.time() * 1000)}",
                    "type": "function",
                    "function": {
                        "name": parsed["name"],
                        "arguments": parsed["arguments"]
                        if isinstance(parsed["arguments"], str)
                        else json.dumps(parsed["arguments"]),
                    },
                }
            elif "function_call" in parsed:
                # OpenAI-style: {"function_call": {"name": "...", "arguments": "..."}}
                fc = parsed["function_call"]
                return {
                    "id": f"call_{idx}_{int(time.time() * 1000)}",
                    "type": "function",
                    "function": {
                        "name": fc.get("name", ""),
                        "arguments": fc.get("arguments", "{}"),
                    },
                }
        except json.JSONDecodeError:
            logger.debug(f"Failed to parse tool call JSON: {match[:100]}...")

        return None

    def _strip_tool_calls(self, content: str) -> str:
        """Remove tool call markers from content for cleaner text response."""
        result = content
        for pattern in self.TOOL_CALL_PATTERNS:
            result = pattern.sub("", result)
        return result.strip()

    async def invoke(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ModelResponse:
        self._load_model()
        assert self._model is not None
        assert self._tokenizer is not None

        start_time = time.perf_counter()

        # Format tools for HuggingFace if provided
        hf_tools = self._format_tools(tools) if tools else None

        # Apply chat template with tools if supported
        try:
            if hf_tools:
                prompt = self._tokenizer.apply_chat_template(
                    messages,
                    tools=hf_tools,  # type: ignore[arg-type]
                    tokenize=False,
                    add_generation_prompt=True,
                )
            else:
                prompt = self._tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
        except TypeError:
            # Model doesn't support tools parameter
            if hf_tools:
                logger.warning(
                    f"Model {self.model_id} tokenizer does not support tools parameter. "
                    "Tool calling may not work correctly."
                )
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

        inputs = self._tokenizer(str(prompt), return_tensors="pt").to(self._model.device)  # type: ignore

        input_len = inputs.input_ids.shape[1]

        # Generate
        outputs = self._model.generate(  # type: ignore
            **inputs,
            max_new_tokens=max_tokens or self.max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            **kwargs,
        )

        # Decode only the new tokens
        generated_tokens = outputs[0][input_len:]
        content = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)

        # Parse tool calls from response
        tool_calls = self._parse_tool_calls(content) if tools else []

        # Clean content if tool calls were found
        if tool_calls:
            clean_content = self._strip_tool_calls(content)
        else:
            clean_content = content

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        usage = {
            "input_tokens": input_len,
            "output_tokens": len(generated_tokens),
            "total_tokens": input_len + len(generated_tokens),
        }

        return ModelResponse(
            content=clean_content,
            tool_calls=tool_calls if tool_calls else None,
            usage=usage,
            metadata={
                "provider": "huggingface-local",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "device": str(self._model.device),
                "raw_content": content if tool_calls else None,  # Include raw if tools parsed
            },
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ModelResponse]:
        self._load_model()
        assert self._model is not None
        assert self._tokenizer is not None

        start_time = time.perf_counter()

        # Format tools for HuggingFace if provided
        hf_tools = self._format_tools(tools) if tools else None

        # Apply chat template with tools if supported
        try:
            if hf_tools:
                prompt = self._tokenizer.apply_chat_template(
                    messages,
                    tools=hf_tools,  # type: ignore[arg-type]
                    tokenize=False,
                    add_generation_prompt=True,
                )
            else:
                prompt = self._tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
        except TypeError:
            if hf_tools:
                logger.warning(f"Model {self.model_id} tokenizer does not support tools parameter.")
            prompt = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )

        inputs = self._tokenizer(str(prompt), return_tensors="pt").to(self._model.device)  # type: ignore
        input_len = inputs.input_ids.shape[1]

        streamer = TextIteratorStreamer(self._tokenizer, skip_prompt=True, skip_special_tokens=True)  # type: ignore

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=max_tokens or self.max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            **kwargs,
        )

        # Run generation in a separate thread to allow streaming
        thread = threading.Thread(target=self._model.generate, kwargs=generation_kwargs)  # type: ignore
        thread.start()

        token_count = 0
        full_content = ""

        # Stream tokens
        for new_text in streamer:
            token_count += 1
            full_content += new_text
            yield ModelResponse(content=new_text, metadata={"is_stream": True})

        thread.join()

        # Parse tool calls from complete response
        tool_calls = self._parse_tool_calls(full_content) if tools else []

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Final response with usage and tool calls
        yield ModelResponse(
            content="",
            tool_calls=tool_calls if tool_calls else None,
            usage={
                "input_tokens": input_len,
                "output_tokens": token_count,
            },
            metadata={
                "provider": "huggingface-local",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "final": True,
            },
        )
