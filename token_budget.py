"""Read-only estimate of AI work still needed for one game."""

import csv
import json
import math
from pathlib import Path


def _items(path):
    if not path.exists():
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("id") is not None:
            found[str(item["id"])] = item
    return found


def estimate_remaining(config, app_id=None):
    folder = Path(config.project_dir(app_id))
    reviews_path = folder / "reviews.csv"
    rows = {}
    if reviews_path.exists():
        with reviews_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = {str(row["recommendationid"]): row for row in csv.DictReader(stream)}
    from analyze_reviews_v3 import needs_deep, should_classify, MIN_LEN_C
    eligible = {rid: row for rid, row in rows.items() if should_classify(row)}
    classified = {rid: item for rid, item in _items(folder / "analysis_v3.jsonl").items() if rid in eligible}
    deep_done = _items(folder / "complaints_v3.jsonl")
    # Stage C follows the first classification. Positives with a negative topic remain eligible.
    deep_targets = {rid for rid, item in classified.items() if needs_deep(item, eligible[rid])}
    pending_b = len(eligible.keys() - classified.keys())
    pending_c = len(deep_targets - deep_done.keys())
    deep_ratio = len(deep_targets) / len(classified) if classified else 0.25
    pending_long = sum(len(eligible[rid]["content"]) >= MIN_LEN_C for rid in eligible.keys() - classified.keys())
    expected_new_c = math.ceil(pending_long * deep_ratio)
    needs_a = pending_b > 0 and not (folder / "themes_v3.json").exists()
    needs_d = bool(eligible) and (pending_b > 0 or pending_c > 0 or not (folder / "summary_v5_cache.json").exists())

    # Conservative per-review allowances. They estimate a budget, not provider billing.
    input_tokens = (12000 if needs_a else 0) + pending_b * 160 + (pending_c + expected_new_c) * 250 + (3500 if needs_d else 0)
    output_tokens = (1500 if needs_a else 0) + pending_b * 90 + (pending_c + expected_new_c) * 180 + (900 if needs_d else 0)
    estimated_usd = round((input_tokens * config.MODEL_COST_INPUT +
                           output_tokens * config.MODEL_COST_OUTPUT) / 1_000_000, 4)
    return {
        "n_reviews": len(eligible), "total_reviews": len(rows),
        "short_reviews": len(rows) - len(eligible),
        "already_done": len(classified), "to_analyze": pending_b,
        "deep_targets": len(deep_targets), "deep_done": len(deep_targets & deep_done.keys()),
        "to_deep": pending_c, "expected_new_deep": expected_new_c,
        "estimated_input_tokens": input_tokens, "estimated_output_tokens": output_tokens,
        "model": config.MODEL, "estimated_usd": estimated_usd,
        "budget_usd": config.BUDGET_USD,
        "within_budget": estimated_usd <= config.BUDGET_USD,
    }
