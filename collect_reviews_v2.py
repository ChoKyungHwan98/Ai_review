"""대표 표본 수집 — 강의 session-12 '샘플링과 대표성' 원칙 준수

절차:
1. Steam query_summary로 한국어 모집단 N, 추천/비추천 비율 확인
2. Cochran 공식으로 목표 오차한계에 맞는 최소 표본 크기 n 계산
3. 부정 리뷰가 최소 MIN_NEG건 이상이 되도록 n을 조정
4. 모집단 비율에 맞춰 긍정/부정을 따로따로 수집 (층화 추출)
5. 하나의 reviews_v2.csv로 저장

결과:
- reviews_v2.csv  (수집된 리뷰)
- sample_design_v2.json  (표본 설계 기록)
"""

import csv
import json
import math
import time
import httpx

from config import cfg

# ─── 설정 ──────────────────────────────────────────────────────────────
def get_app_id(): return cfg.APP_ID
def get_lang(): return cfg.LANG
def get_target_error(): return cfg.TARGET_ERROR_PCT
def get_min_neg(): return cfg.MIN_NEG_REVIEWS
def get_z95(): return cfg.Z_95
def get_out_csv(): return cfg.REVIEWS_CSV
def get_out_json(): return cfg.SAMPLE_JSON
def get_url(): return cfg.STEAM_API_URL

# ─── 1단계: 모집단 조회 ───────────────────────────────────────────────

def fetch_population():
    """Steam query_summary에서 한국어 리뷰 모집단 통계를 가져온다."""
    r = httpx.get(get_url().format(appid=get_app_id()), params={
        "json": 1, "filter": "recent", "language": get_lang(),
        "review_type": "all", "purchase_type": "all",
        "num_per_page": 0, "filter_offtopic_activity": 0,
    }, timeout=30.0)
    r.raise_for_status()
    qs = r.json().get("query_summary", {})
    total = qs.get("total_reviews", 0)
    positive = qs.get("total_positive", 0)
    negative = qs.get("total_negative", 0)
    score = qs.get("review_score_desc", "")
    if total == 0:
        raise ValueError("모집단 조회 실패: total_reviews=0")
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "pos_rate": positive / total,
        "neg_rate": negative / total,
        "score": score,
    }


# ─── 2단계: 표본 크기 계산 ─────────────────────────────────────────────

def cochran_n(N, p=0.5, z=get_z95(), e=0.05):
    """유한모집단 보정 Cochran 공식."""
    n0 = (z ** 2 * p * (1 - p)) / (e ** 2)
    n = n0 / (1 + (n0 - 1) / N) if N > 0 else n0
    return math.ceil(n)


def margin_of_error(n, N, p=0.5, z=get_z95()):
    """현재 n으로 도달 가능한 오차한계 (%)."""
    if n <= 0 or N <= 0: return 100.0
    if n >= N: return 0.0
    se2 = (p * (1 - p) / n) * (N - n) / (N - 1)
    return z * math.sqrt(max(se2, 0)) * 100


def decide_sample_size(pop):
    """목표 오차한계와 최소 부정 건수를 모두 만족하는 n 결정."""
    custom_size = getattr(cfg, "CUSTOM_SAMPLE_SIZE", None)
    if custom_size is not None and custom_size > 0:
        n = min(custom_size, pop["total"])
        n_pos = math.ceil(n * pop["pos_rate"])
        n_neg = n - n_pos
        actual_error = margin_of_error(n, pop["total"])
        return {
            "n_total": n,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "error_pct": round(actual_error, 2),
            "reason": f"사용자 지정 커스텀 수집 건수 {n}건 적용 (모집단 비율 유지)",
        }

    e = get_target_error() / 100
    n_by_error = cochran_n(pop["total"], p=0.5, z=get_z95(), e=e)

    # 부정 리뷰 최소 건수 확보를 위한 n
    neg_rate = pop["neg_rate"]
    if neg_rate > 0:
        n_for_neg = math.ceil(get_min_neg() / neg_rate)
    else:
        n_for_neg = n_by_error

    n = max(n_by_error, n_for_neg)

    # 모집단보다 크면 모집단 전체로
    n = min(n, pop["total"])

    n_pos = math.ceil(n * pop["pos_rate"])
    n_neg = n - n_pos  # 나머지 전부 부정

    actual_error = margin_of_error(n, pop["total"])

    return {
        "n_total": n,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "error_pct": round(actual_error, 2),
        "reason": f"오차 ±{get_target_error()}% 충족 필요 n={n_by_error}, 부정 최소 {get_min_neg()}건 필요 n={n_for_neg} → max={n}",
    }


# ─── 3단계: 수집 ──────────────────────────────────────────────────────

def collect_reviews(review_type, target, existing_ids):
    """review_type='positive' 또는 'negative'로 target건 수집."""
    collected = []
    cursor = "*"
    while len(collected) < target:
        r = httpx.get(get_url().format(appid=get_app_id()), params={
            "json": 1, "filter": "recent", "language": get_lang(),
            "review_type": review_type, "purchase_type": "all",
            "num_per_page": 100, "cursor": cursor,
            "filter_offtopic_activity": 0,
        }, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        reviews = data.get("reviews", [])
        if not reviews:
            print(f"  [{review_type}] 더 이상 리뷰 없음. 중단.")
            break
        new_count = 0
        for rv in reviews:
            rid = str(rv.get("recommendationid"))
            if rid in existing_ids:
                continue
            existing_ids.add(rid)
            author = rv.get("author", {})
            collected.append({
                "recommendationid": rid,
                "content": rv.get("review", "").replace("\r", " ").replace("\n", " ").strip(),
                "voted_up": 1 if rv.get("voted_up") else 0,
                "votes_up": rv.get("votes_up", 0),
                "votes_funny": rv.get("votes_funny", 0),
                "weighted_vote_score": rv.get("weighted_vote_score", "0"),
                "playtime_at_review_min": author.get("playtime_at_review", 0),
                "playtime_forever_min": author.get("playtime_forever", 0),
                "author_steamid": author.get("steamid", ""),
                "timestamp_created": rv.get("timestamp_created", 0),
            })
            new_count += 1
            if len(collected) >= target:
                break
        print(f"  [{review_type}] {len(collected)}/{target} (이번 페이지 +{new_count})")
        next_cursor = data.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(0.6)
    return collected


# ─── 메인 ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("📊 대표 표본 수집 (강의 session-12 원칙)")
    print("=" * 60)

    # 1) 모집단 조회
    print("\n[1] Steam 한국어 모집단 조회…")
    pop = fetch_population()
    print(f"  전체: {pop['total']:,}건")
    print(f"  긍정: {pop['positive']:,}건 ({pop['pos_rate']*100:.1f}%)")
    print(f"  부정: {pop['negative']:,}건 ({pop['neg_rate']*100:.1f}%)")
    print(f"  Steam 평가: {pop['score']}")

    # 2) 표본 크기 결정
    print("\n[2] 표본 크기 계산…")
    design = decide_sample_size(pop)
    print(f"  목표: 오차 ±{get_target_error()}% + 부정 최소 {get_min_neg()}건")
    print(f"  결정: 총 {design['n_total']}건 (긍정 {design['n_pos']} / 부정 {design['n_neg']})")
    print(f"  실제 오차: ±{design['error_pct']}%")
    print(f"  사유: {design['reason']}")

    # 3) 수집
    print("\n[3] 리뷰 수집 시작…")
    seen_ids = set()

    print(f"\n  ── 긍정 리뷰 {design['n_pos']}건 수집 ──")
    pos_reviews = collect_reviews("positive", design["n_pos"], seen_ids)

    print(f"\n  ── 부정 리뷰 {design['n_neg']}건 수집 ──")
    neg_reviews = collect_reviews("negative", design["n_neg"], seen_ids)

    all_reviews = pos_reviews + neg_reviews

    # 4) CSV 저장
    if not all_reviews:
        print("❌ 수집된 리뷰가 없습니다.")
        return

    fieldnames = list(all_reviews[0].keys())
    with open(get_out_csv(), "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_reviews)

    # 5) 설계 기록 저장
    actual_pos = sum(1 for r in all_reviews if r["voted_up"] == 1)
    actual_neg = sum(1 for r in all_reviews if r["voted_up"] == 0)
    actual_total = len(all_reviews)
    actual_error = margin_of_error(actual_total, pop["total"])

    record = {
        "population": pop,
        "design": design,
        "actual": {
            "total": actual_total,
            "positive": actual_pos,
            "negative": actual_neg,
            "pos_rate": round(actual_pos / actual_total, 4) if actual_total else 0,
            "neg_rate": round(actual_neg / actual_total, 4) if actual_total else 0,
            "error_pct": round(actual_error, 2),
        },
        "params": {
            "target_error_pct": get_target_error(),
            "min_neg": get_min_neg(),
            "confidence_level": 0.95,
            "language": get_lang(),
            "app_id": get_app_id(),
        },
    }
    with open(get_out_json(), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # 6) 요약
    print(f"\n{'='*60}")
    print(f"✅ 수집 완료!")
    print(f"  총 {actual_total}건 → {get_out_csv()}")
    print(f"  긍정: {actual_pos}건 ({actual_pos/actual_total*100:.1f}%)")
    print(f"  부정: {actual_neg}건 ({actual_neg/actual_total*100:.1f}%)")
    print(f"  실제 오차: ±{actual_error:.2f}%")
    print(f"  설계 기록: {get_out_json()}")

    # 비율 검증
    ratio_diff = abs(actual_pos / actual_total - pop["pos_rate"]) * 100
    if ratio_diff <= 2:
        print(f"  ✅ 모집단 비율과 ±{ratio_diff:.1f}%p 이내 일치 — 대표성 확보")
    else:
        print(f"  ⚠️ 모집단 비율과 {ratio_diff:.1f}%p 차이 — 표본 부족 가능")

    avg_play = sum(r["playtime_forever_min"] for r in all_reviews) / max(actual_total, 1) / 60
    print(f"  평균 플레이타임: {avg_play:.1f}시간")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
