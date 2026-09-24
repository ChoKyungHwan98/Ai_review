"""Conservative per-run OpenRouter spending guard.

This blocks requests before dispatch using published prices, UTF-8 input bytes
as an upper-bound token allowance, and the request's output token cap.
Provider billing can still differ; this is not an account-level spending limit.
"""
import json
import threading


class BudgetExceeded(RuntimeError):
    pass


class BudgetGuard:
    def __init__(self, limit_usd, input_per_million, output_per_million, request_per_million=0):
        self.limit = float(limit_usd)
        self.input_rate = float(input_per_million)
        self.output_rate = float(output_per_million)
        self.request_rate = float(request_per_million)
        self.spent = 0.0
        self.reserved = 0.0
        self.lock = threading.Lock()

    def reserve(self, messages, max_tokens):
        encoded = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        input_allowance = len(encoded) + 512
        allowance = (input_allowance * self.input_rate + max_tokens * self.output_rate +
                     self.request_rate) / 1_000_000
        with self.lock:
            if self.spent + self.reserved + allowance > self.limit:
                raise BudgetExceeded("설정한 분석 예산을 넘을 수 있어 다음 AI 호출을 시작하지 않았습니다")
            self.reserved += allowance
        return allowance

    def finish(self, allowance, usage=None):
        usage = usage or {}
        if usage.get("prompt_tokens") is not None and usage.get("completion_tokens") is not None:
            actual = ((int(usage["prompt_tokens"]) * self.input_rate +
                       int(usage["completion_tokens"]) * self.output_rate +
                       self.request_rate) / 1_000_000)
        else:
            actual = allowance  # Uncertain response: keep the reservation as spent.
        with self.lock:
            self.reserved = max(0.0, self.reserved - allowance)
            self.spent += actual


_active = None


def activate(model, limit_usd):
    global _active
    _active = BudgetGuard(limit_usd, model["input_cost"], model["output_cost"], model["request_cost"])
    return _active


def current():
    return _active


def clear():
    global _active
    _active = None
