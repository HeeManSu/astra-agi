from collections.abc import AsyncIterator
import logging
import threading
import time
from typing import Any

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
    Runs models locally on CPU/GPU.
    """

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

        # Apply chat template
        # Note: tools are not natively supported by this simple implementation yet
        # unless the model template supports them specificially.
        # For now we ignore tools or could warn.
        if tools:
            logger.warning("Tools are not currently supported in HuggingFaceLocal provider.")

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

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        usage = {
            "input_tokens": input_len,
            "output_tokens": len(generated_tokens),
            "total_tokens": input_len + len(generated_tokens),
        }

        return ModelResponse(
            content=content,
            usage=usage,
            metadata={
                "provider": "huggingface-local",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "device": str(self._model.device),
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

        if tools:
            logger.warning("Tools are not currently supported in HuggingFaceLocal provider.")

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

        # In a real async loop we might want to run this iteration differently
        # but this simple yield loop works for many cases if not purely async blocked.
        # Since transformers is blocking, we rely on the thread.
        for new_text in streamer:
            token_count += 1  # Approximation
            yield ModelResponse(content=new_text, metadata={"is_stream": True})

        thread.join()

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        yield ModelResponse(
            content="",
            usage={
                "input_tokens": input_len,
                "output_tokens": token_count,  # Approx
            },
            metadata={
                "provider": "huggingface-local",
                "model_id": self.model_id,
                "latency_ms": latency_ms,
                "final": True,
            },
        )
