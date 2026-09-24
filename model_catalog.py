"""Live OpenRouter text-model catalog and per-token prices.

No invented fallback prices: when the catalog is unavailable, a new run waits.
"""
import math
import threading
import time

import httpx


URL = "https://openrouter.ai/api/v1/models"
TTL_SECONDS = 15 * 60
_lock = threading.Lock()
_cached = []
_fetched_at = 0.0


def _price(value):
    try:
        result = float(value) * 1_000_000
        return result if math.isfinite(result) and result >= 0 else None
    except (TypeError, ValueError):
        return None


def list_models(force=False):
    global _cached, _fetched_at
    with _lock:
        if _cached and not force and time.monotonic() - _fetched_at < TTL_SECONDS:
            return list(_cached)
    response = httpx.get(URL, timeout=15.0)
    response.raise_for_status()
    models = []
    for raw in response.json().get("data", []):
        architecture = raw.get("architecture") or {}
        inputs = architecture.get("input_modalities") or []
        outputs = architecture.get("output_modalities") or []
        if "text" not in inputs or "text" not in outputs:
            continue
        pricing = raw.get("pricing") or {}
        prompt = _price(pricing.get("prompt"))
        completion = _price(pricing.get("completion"))
        request = _price(pricing.get("request", 0))
        if prompt is None or completion is None or request is None:
            continue
        model_id = raw.get("id")
        if not model_id:
            continue
        context_length = int(raw.get("context_length") or 0)
        if context_length < 32768:
            continue
        params = raw.get("supported_parameters") or []
        models.append({
            "id": model_id, "name": raw.get("name") or model_id,
            "input_cost": prompt, "output_cost": completion,
            "request_cost": request, "free": prompt == completion == request == 0,
            "context_length": context_length,
            "json_schema": "response_format" in params,
        })
    if not models:
        raise ValueError("사용 가능한 텍스트 분석 모델을 찾지 못했습니다")
    models.sort(key=lambda m: (not m["free"], m["input_cost"] + m["output_cost"], m["name"].casefold()))
    with _lock:
        _cached, _fetched_at = models, time.monotonic()
    return list(models)


def get_model(model_id):
    return next((model for model in list_models() if model["id"] == model_id), None)
