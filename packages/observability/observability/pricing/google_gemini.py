from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


_PRICING_PATH = Path(__file__).with_suffix("").with_name("google_gemini_pricing.json")


@dataclass
class GeminiModelPricing:
    model_id: str
    input_tokens_per_1k: float | None = None
    output_tokens_per_1k: float | None = None


_PRICING_CACHE: dict[str, GeminiModelPricing] = {}


def _load_pricing() -> None:
    global _PRICING_CACHE
    if _PRICING_CACHE:
        return
    try:
        with _PRICING_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        _PRICING_CACHE = {}
        return
    models = data.get("models") or []
    for m in models:
        model_id = m.get("id")
        if not isinstance(model_id, str):
            continue
        pricing = m.get("pricing") or {}
        _PRICING_CACHE[model_id] = GeminiModelPricing(
            model_id=model_id,
            input_tokens_per_1k=pricing.get("input_tokens_per_1k"),
            output_tokens_per_1k=pricing.get("output_tokens_per_1k"),
        )


def get_gemini_pricing(model: str) -> GeminiModelPricing | None:
    if not _PRICING_CACHE:
        _load_pricing()
    return _PRICING_CACHE.get(model)


@dataclass
class GeminiUsageCost:
    total_usd: float
    input_usd: float
    output_usd: float


def estimate_gemini_usage_cost_breakdown(
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> GeminiUsageCost | None:
    pricing = get_gemini_pricing(model)
    if pricing is None:
        return None

    input_cost = 0.0
    output_cost = 0.0

    if isinstance(prompt_tokens, int) and pricing.input_tokens_per_1k is not None:
        input_cost = (prompt_tokens / 1000.0) * pricing.input_tokens_per_1k

    if isinstance(completion_tokens, int) and pricing.output_tokens_per_1k is not None:
        output_cost = (completion_tokens / 1000.0) * pricing.output_tokens_per_1k

    total_cost = input_cost + output_cost

    if total_cost == 0.0 and input_cost == 0.0 and output_cost == 0.0:
        return None

    return GeminiUsageCost(
        total_usd=total_cost,
        input_usd=input_cost,
        output_usd=output_cost
    )


def estimate_gemini_usage_cost(
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float | None:
    breakdown = estimate_gemini_usage_cost_breakdown(model, prompt_tokens, completion_tokens)
    return breakdown.total_usd if breakdown else None

