"""Read-only evidence for the visual review dashboard. No AI/API calls.

Counts describe collected reviews, not all players. Topic sentiment and Steam
recommendation are different dimensions; one review may contain both sentiments.
"""
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import decisions

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
    names = ("reviews.csv", "analysis_v3.jsonl", "sample_design.json", "complaints_v3.jsonl")
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
    complaints = []
    if (folder / "complaints_v3.jsonl").exists():
        with (folder / "complaints_v3.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    item = json.loads(line) if line.strip() else None
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and str(item.get("id")) in reviews:
                    complaints.append(item)
    return reviews, analyzed, design, skipped, complaints


def topic_members(analyzed, alias=None):
    """주제별 칭찬·불만 리뷰 번호. alias는 사람이 다듬은 주제(합치기·이름 바꾸기·숨기기)."""
    members = {}
    alias = alias or {}
    for rid, item in analyzed.items():
        for pair in item.get("t") or []:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                continue
            name, sentiment = pair
            if not isinstance(name, str) or name == "기타" or sentiment not in ("P", "N"):
                continue
            name = decisions.resolve(name, alias)
            if name is None:
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
    reviews, analyzed, design, skipped, complaints = source
    alias = decisions.load(directory)["alias"]
    members = topic_members(analyzed, alias)
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
            "deep": build_deep(reviews, analyzed, members, complaints, app_id, alias),
            "fun_denominator": len(liked),
            "fun": [{"name": f, "desc": FUN[f], "count": c, "share": round(c / len(liked) * 100, 1)}
                    for f, c in fun_counts.most_common()]}


# ── 심층 분석: AI를 다시 부르지 않고 이미 저장된 결과만 다시 센다 ──────────────
EARLY_HOURS = 20
STOPWORDS = {"게임", "너무", "진짜", "정말", "많이", "조금", "좀", "계속", "자꾸", "때문", "문제", "현상",
             "발생", "있음", "없음", "있다", "없다", "하는", "되는", "되지", "않음", "않는", "안됨", "경우",
             "부분", "관련", "상태", "이후", "이상", "그냥", "매우", "가끔", "자주", "일부", "전체", "유저",
             "플레이", "플레이어", "느낌", "생각", "수준", "정도", "해서", "하고", "으로", "에서"}
SUFFIXES = ("에서는", "으로는", "에서", "으로", "이나", "까지", "부터", "하고", "해서", "하면", "하는", "되는",
            "됨", "함", "음", "이", "가", "은", "는", "을", "를", "에", "의", "도", "로", "과", "와", "만")
REQUEST_MARKS = ("해주", "해 주", "했으면", "좋겠", "추가", "수정", "개선", "희망", "부탁", "늘려", "줄여",
                 "바꿔", "복구", "지원", "넣어", "고쳐", "상향", "하향", "가능하게", "필요")
VAGUE = {"버그 수정", "버그 개선", "개선 필요", "최적화 필요", "최적화 개선", "수정 필요", "편의성 개선"}


def words(text):
    """짧은 한국어 문장을 뜻 있는 낱말로. 형태소 분석기 없이 흔한 조사·어미만 떼어 낸다."""
    out = set()
    for w in re.findall(r"[0-9A-Za-z가-힣]+", text or ""):
        for suffix in SUFFIXES:
            if len(w) > len(suffix) + 1 and w.endswith(suffix):
                w = w[: -len(suffix)]
                break
        if len(w) >= 2 and w not in STOPWORDS:
            out.add(w)
    return out


def votes(row):
    return int(number(row.get("votes_up")) or 0)


def build_deep(reviews, analyzed, members, complaints, app_id, alias=None):
    parts = {}  # 주제 → [(리뷰 번호, 문제, 원인, 제안)]
    for item in complaints:
        rid = str(item["id"])
        for p in item.get("p") or []:
            name = decisions.resolve(p.get("t"), alias or {}) if isinstance(p, dict) and p.get("t") else None
            if name:
                parts.setdefault(name, []).append((rid, str(p.get("prob") or ""), str(p.get("why") or ""), str(p.get("fix") or "")))
    focus = sorted((name for name, g in members.items() if g["N"]),
                   key=lambda name: (-(len(members[name]["N"]) > len(members[name]["P"])), -len(members[name]["N"])))[:4]

    # ① 불만 세부 원인: 주제별 불만 문장에서 여러 리뷰가 함께 쓴 낱말
    causes = []
    for name in focus:
        rows = parts.get(name) or []
        seen, example = Counter(), {}
        for rid, prob, why, _ in rows:
            for w in sorted(words(f"{prob} {why}") - words(name)):
                seen[w] += 1
                example.setdefault(w, prob or why)
        ranked = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
        terms = [{"word": w, "count": c, "example": example[w][:60]} for w, c in ranked if c >= 2]
        causes.append({"theme": name, "reviews": len({r[0] for r in rows}), "terms": terms})

    # ② 초반 이탈: 20시간 전에 비추천한 리뷰와 그 뒤에 비추천한 리뷰가 불만으로 꼽은 주제
    early, later = Counter(), Counter()
    early_n = later_n = 0
    for rid, item in analyzed.items():
        row = reviews[rid]
        hours = review_hours(row)
        if is_positive(row) or hours is None:
            continue
        names = {decisions.resolve(n, alias or {}) for n, s in (item.get("t") or []) if s == "N" and n != "기타"} - {None}
        if hours < EARLY_HOURS:
            early_n += 1
            early.update(names)
        else:
            later_n += 1
            later.update(names)
    share = lambda c, n: round(c / n * 100, 1) if n else None
    churn_topics = [{"name": k, "early": early[k], "later": later[k],
                     "early_share": share(early[k], early_n), "later_share": share(later[k], later_n)}
                    for k in sorted(set(early) | set(later), key=lambda k: (-early[k], -later[k]))[:6]]

    # ③ 공감 많은 불만: 다른 유저가 "도움됨"을 누른 수
    total_votes = sum(votes(reviews[rid]) for g in members.values() for rid in g["N"]) or 0
    total_neg = sum(len(g["N"]) for g in members.values()) or 0
    agreed = sorted(({"name": name, "neg": len(g["N"]), "votes": sum(votes(reviews[rid]) for rid in g["N"])}
                     for name, g in members.items() if g["N"]), key=lambda t: -t["votes"])[:6]
    for t in agreed:
        t["vote_share"] = share(t["votes"], total_votes)
        t["count_share"] = share(t["neg"], total_neg)
    loudest = sorted({rid for g in members.values() for rid in g["N"]}, key=lambda rid: -votes(reviews[rid]))[:3]
    top_reviews = [dict(excerpt(reviews[rid], app_id, 160),
                        themes=[n for n, g in members.items() if rid in g["N"]]) for rid in loudest if votes(reviews[rid]) > 0]

    # ④ 유저가 원하는 것: 불만 리뷰의 구체적인 요청. 같은 문장은 합치고 공감 순
    wants = {}
    for name, rows in parts.items():
        for rid, _, _, fix in rows:
            text = " ".join(fix.split())
            if len(text) < 6 or text in VAGUE or not any(m in text for m in REQUEST_MARKS):
                continue
            key = re.sub(r"\s+", "", text)
            w = wants.setdefault(key, {"text": text[:60], "theme": name, "count": 0, "votes": 0})
            w["count"] += 1
            w["votes"] += votes(reviews[rid])
    wants = sorted(wants.values(), key=lambda w: (-w["count"], -w["votes"]))[:8]

    return {"early_hours": EARLY_HOURS, "has_complaints": bool(complaints), "causes": causes,
            "churn": {"early_n": early_n, "later_n": later_n, "topics": churn_topics},
            "agreed": {"topics": agreed, "total_votes": total_votes, "reviews": top_reviews},
            "wants": wants}


def evidence_page(directory, app_id, theme, sentiment="N", page=1):
    source = load_sources(directory)
    if source is None:
        return None
    reviews, analyzed = source[0], source[1]
    group = topic_members(analyzed, decisions.load(directory)["alias"]).get(theme)
    if group is None:
        return None
    ids = group[sentiment] if sentiment in ("P", "N") else group["P"] | group["N"]
    ordered = sorted_ids(ids, reviews)
    return {"theme": theme, "sentiment": sentiment, "total": len(ordered), "page": page,
            "page_size": 20, "reviews": [excerpt(reviews[rid], app_id, limit=20000)
                                         for rid in ordered[(page - 1) * 20:page * 20]]}
