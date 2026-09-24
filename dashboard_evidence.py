"""Read-only evidence for the visual review dashboard. No AI/API calls.

Counts describe collected reviews, not all players. Topic sentiment and Steam
recommendation are different dimensions; one review may contain both sentiments.
"""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

BUCKETS = ((0, 2, "2시간 미만"), (2, 20, "2~20시간"),
           (20, 100, "20~100시간"), (100, float("inf"), "100시간 이상"))
FUN = {"감각": "보고 듣는 즐거움", "판타지": "다른 존재가 되는 경험",
       "이야기": "줄거리와 전개", "도전": "어려움을 넘는 성취",
       "함께": "다른 사람과 어울림", "발견": "탐험과 새로운 발견",
       "표현": "꾸미고 나를 드러냄", "몰두": "시간 가는 줄 모르는 반복"}


def number(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def review_hours(row):
    # Zero is a valid value. Current total hours cannot stand in for hours at review.
    minutes = number(row.get("playtime_at_review_min"))
    return minutes / 60 if minutes is not None and minutes >= 0 else None


def bucket_index(row):
    hours = review_hours(row)
    return next((i for i, (lo, hi, _) in enumerate(BUCKETS)
                 if hours is not None and lo <= hours < hi), None)


def is_positive(row):
    return str(row.get("voted_up", "")).lower() in ("1", "true")


def load_sources(directory):
    folder = Path(directory)
    names = ("reviews.csv", "analysis_v3.jsonl", "sample_design.json")
    stamps = tuple((folder / name).stat().st_mtime_ns if (folder / name).exists() else None
                   for name in names)
    return _load_sources(str(folder), stamps)


@lru_cache(maxsize=8)
def _load_sources(directory, stamps):
    folder = Path(directory)
    if not (folder / "reviews.csv").exists() or not (folder / "analysis_v3.jsonl").exists():
        return None
    with (folder / "reviews.csv").open(encoding="utf-8-sig", newline="") as stream:
        reviews = {str(r["recommendationid"]): r for r in csv.DictReader(stream)}
    analyzed = {}
    skipped = 0
    with (folder / "analysis_v3.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            if not isinstance(item, dict) or str(item.get("id")) not in reviews:
                skipped += 1
                continue
            analyzed[str(item["id"])] = item
    design = {}
    if (folder / "sample_design.json").exists():
        with (folder / "sample_design.json").open(encoding="utf-8") as stream:
            design = json.load(stream)
    return reviews, analyzed, design, skipped


def topic_members(analyzed):
    members = {}
    for rid, item in analyzed.items():
        for pair in item.get("t") or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            name, sentiment = pair
            if not isinstance(name, str) or name == "기타" or sentiment not in ("P", "N"):
                continue
            group = members.setdefault(name, {"P": set(), "N": set()})
            group[sentiment].add(rid)
    return members


def excerpt(row, app_id, limit=260):
    content = row.get("content") or ""
    author = str(row.get("author_steamid") or "")
    return {"id": str(row["recommendationid"]), "content": content[:limit],
            "truncated": len(content) > limit, "recommended": is_positive(row),
            "hours": review_hours(row), "helpful": int(number(row.get("votes_up")) or 0),
            "url": f"https://steamcommunity.com/profiles/{author}/recommended/{int(app_id)}/"
            if author.isdigit() else None}


def sorted_ids(ids, reviews):
    return sorted(ids, key=lambda rid: (-(number(reviews[rid].get("votes_up")) or 0),
                                       -(number(reviews[rid].get("timestamp_created")) or 0), rid))


def build_evidence(directory, app_id):
    source = load_sources(directory)
    if source is None:
        return None
    reviews, analyzed, design, skipped = source
    members = topic_members(analyzed)
    n = len(reviews)
    up = sum(is_positive(r) for r in reviews.values())
    base = up / n if n else None
    cohorts = []
    for index, (_, _, label) in enumerate(BUCKETS):
        ids = {rid for rid, row in reviews.items() if bucket_index(row) == index}
        analyzed_ids = ids & analyzed.keys()
        negative = sum(not is_positive(reviews[rid]) for rid in ids)
        cohorts.append({"label": label, "n": len(ids), "analyzed": len(analyzed_ids),
                        "negative": negative, "negative_rate": round(negative / len(ids) * 100, 1) if ids else None,
                        "small": len(ids) < 30})
    themes = []
    for name, group in members.items():
        ids = group["P"] | group["N"]
        remaining_n = n - len(ids)
        without = ((up - sum(is_positive(reviews[rid]) for rid in ids)) / remaining_n
                   if remaining_n else None)
        cells = []
        for index, cohort in enumerate(cohorts):
            count = sum(bucket_index(reviews[rid]) == index for rid in group["N"])
            cells.append({"count": count, "denominator": cohort["analyzed"],
                          "rate": round(count / cohort["analyzed"] * 100, 1) if cohort["analyzed"] else None})
        themes.append({"name": name, "pos": len(group["P"]), "neg": len(group["N"]),
                       "mentions": len(ids), "negative_recommended": sum(is_positive(reviews[rid]) for rid in group["N"]),
                       "exclusion_delta": round((without - base) * 100, 2) if without is not None else None,
                       "cells": cells,
                       "examples": {s: [excerpt(reviews[rid], app_id) for rid in sorted_ids(group[s], reviews)[:2]]
                                    for s in ("P", "N")}})
    complaint_ids = set().union(*(g["N"] for g in members.values())) if members else set()
    mood = Counter(item.get("s") if item.get("s") in ("P", "M", "N") else "U"
                   for item in analyzed.values())
    liked = [a for a in analyzed.values() if a.get("s") in ("P", "M")]
    fun_counts = Counter(f for a in liked for f in set(a.get("f") or []) if f in FUN)
    timestamps = [number(r.get("timestamp_created")) for r in reviews.values()]
    timestamps = [t for t in timestamps if t is not None and t > 0]
    day = lambda stamp: datetime.fromtimestamp(stamp, timezone.utc).strftime("%Y-%m-%d")
    return {"counts": {"collected": n, "analyzed": len(analyzed), "negative": n - up,
                       "complaint_reviews": len(complaint_ids),
                       "recommended_complaints": sum(is_positive(reviews[rid]) for rid in complaint_ids),
                       "unknown_playtime": sum(review_hours(r) is None for r in reviews.values()),
                       "skipped_analysis": skipped},
            "period": {"start": day(min(timestamps)), "end": day(max(timestamps))} if timestamps else None,
            "language": (design.get("params") or {}).get("language", "unknown"),
            "sample_negative_rate": round((n - up) / n * 100, 1) if n else None,
            "mood": {key: mood[key] for key in ("P", "M", "N", "U")},
            "themes": sorted(themes, key=lambda t: (-t["mentions"], t["name"])),
            "cohorts": cohorts,
            "fun_denominator": len(liked),
            "fun": [{"name": f, "desc": FUN[f], "count": c, "share": round(c / len(liked) * 100, 1)}
                    for f, c in fun_counts.most_common()]}


def evidence_page(directory, app_id, theme, sentiment="N", page=1):
    source = load_sources(directory)
    if source is None:
        return None
    reviews, analyzed, _, _ = source
    group = topic_members(analyzed).get(theme)
    if group is None:
        return None
    ids = group[sentiment] if sentiment in ("P", "N") else group["P"] | group["N"]
    ordered = sorted_ids(ids, reviews)
    return {"theme": theme, "sentiment": sentiment, "total": len(ordered), "page": page,
            "page_size": 20, "reviews": [excerpt(reviews[rid], app_id, limit=20000)
                                         for rid in ordered[(page - 1) * 20:page * 20]]}
