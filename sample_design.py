"""표본 설계 검증 — 모집단 조회 + 95% 신뢰수준 표본 크기 + 층화 추출 권장량

강의 session-12(샘플링과 대표성) + session-25(확률과 신뢰도 해석) 반영.

산출:
1) 팰월드 한국어 리뷰 모집단 N, 추천/비추천 비율 (Steam query_summary)
2) 95% 신뢰수준에서 필요한 최소 표본 크기 n (오차한계 e=3%, 5%, 7%)
3) 모집단 비율을 따르는 층화 추출 권장량 (n_pos, n_neg)
4) 현재 수집한 표본(추천 288, 비추천 112)의 적정성 평가

결과: sample_design.json + 콘솔 출력
"""

import json
import math
import httpx

APP_ID = 1623730  # Palworld
LANG = "koreana"
URL = f"https://store.steampowered.com/appreviews/{APP_ID}"
Z_95 = 1.96  # 95% 신뢰수준


def fetch_population_summary():
    """Steam Storefront API: 한국어 리뷰 모집단 통계 조회.

    review_type=all 로 한 번, positive/negative로 각 한 번씩 호출해서
    한국어 한정 전체/긍정/부정 모집단 N을 가져온다.
    """
    out = {}
    for rt in ["all", "positive", "negative"]:
        r = httpx.get(URL, params={
            "json": 1,
            "filter": "recent",
            "language": LANG,
            "review_type": rt,
            "purchase_type": "all",
            "num_per_page": 0,        # 본문은 안 받고 summary만
            "filter_offtopic_activity": 0,
        }, timeout=30.0)
        r.raise_for_status()
        qs = r.json().get("query_summary", {})
        out[rt] = qs
    return out


def cochran_sample_size(N: int, p: float = 0.5, z: float = Z_95, e: float = 0.05) -> int:
    """유한모집단 보정이 적용된 Cochran 표본 크기 공식.

    n0 = (z^2 * p * (1-p)) / e^2
    n  = n0 / (1 + (n0 - 1) / N)
    """
    n0 = (z * z * p * (1 - p)) / (e * e)
    n  = n0 / (1 + (n0 - 1) / N) if N > 0 else n0
    return math.ceil(n)


def margin_of_error(n: int, N: int, p: float = 0.5, z: float = Z_95) -> float:
    """현재 표본 n으로 도달 가능한 오차한계 e (%) 계산."""
    if n <= 0 or N <= 0: return 100.0
    # n = n0 / (1 + (n0 - 1)/N) → n0 = n*N / (N - n + n_correction)
    # 단순화: e = z * sqrt(p(1-p)/n * (N-n)/(N-1))
    if n >= N: return 0.0
    se2 = (p * (1 - p) / n) * (N - n) / (N - 1)
    e = z * math.sqrt(max(se2, 0))
    return e * 100  # %


def main():
    print("=" * 60)
    print("📊 팰월드 한국어 리뷰 모집단 조회 (Steam query_summary)")
    print("=" * 60)
    pop = fetch_population_summary()

    # review_type=all 응답의 모든 필드 dump (디버그)
    print("\n[전체 한국어 query_summary 전체 응답]")
    for k, v in pop["all"].items():
        print(f"  {k}: {v}")

    N_all = pop["all"].get("total_reviews", 0)
    # Steam은 total_positive/total_negative를 review_type=all 응답에 직접 안 줌.
    # 그래서 무편향 수집한 첫 300건의 voted_up 비율로 모집단 비율을 추정한다.
    # (강의 session-12: "랜덤 표본의 비율은 모집단 비율의 무편향 추정치")
    INITIAL_UNBIASED_N = 300
    INITIAL_POS = 288   # collect_reviews.py 1차 수집 (review_type=all)
    INITIAL_NEG = 12
    r_pos = INITIAL_POS / INITIAL_UNBIASED_N
    r_neg = INITIAL_NEG / INITIAL_UNBIASED_N
    N_pos = int(N_all * r_pos)
    N_neg = N_all - N_pos
    score = pop["all"].get("review_score_desc", "")

    print(f"\n전체 한국어 리뷰    N_all = {N_all:>7,}건")
    print(f"  ├─ 추천(Positive) N_pos ≈ {N_pos:>7,}건  ({r_pos*100:.1f}%)  ← 첫 300건 무편향 표본에서 추정")
    print(f"  └─ 비추천(Negative) N_neg ≈ {N_neg:>7,}건  ({r_neg*100:.1f}%)")
    print(f"Steam 자체 평가: {score}")

    # 1) 95% 신뢰수준 표본 크기 (오차한계별)
    print(f"\n{'='*60}")
    print(f"📐 95% 신뢰수준 최소 표본 크기 (Cochran + 유한모집단 보정)")
    print(f"{'='*60}")
    print(f"공식: n = n0 / (1 + (n0-1)/N),  n0 = z²·p(1-p)/e²")
    print(f"가정: p=0.5 (가장 보수적), z=1.96\n")

    table = []
    for e_pct in [3, 5, 7, 10]:
        e = e_pct / 100
        n_required = cochran_sample_size(N_all, p=0.5, z=Z_95, e=e)
        table.append((e_pct, n_required))
        print(f"  오차한계 ±{e_pct}%p → 최소 표본 n = {n_required:>5}건")

    # 2) 층화 추출 권장량 (모집단 비율 유지)
    print(f"\n{'='*60}")
    print(f"📐 층화 추출 권장량 (모집단 비율 유지, 오차 ±5%p 기준)")
    print(f"{'='*60}")
    n_total_5pct = cochran_sample_size(N_all, p=0.5, z=Z_95, e=0.05)
    n_pos_target = math.ceil(n_total_5pct * r_pos)
    n_neg_target = math.ceil(n_total_5pct * r_neg)
    print(f"  총 표본    n = {n_total_5pct}건")
    print(f"  ├─ 추천 표본  ≈ {n_pos_target}건  (모집단 비율 {r_pos*100:.1f}%)")
    print(f"  └─ 비추천 표본 ≈ {n_neg_target}건  (모집단 비율 {r_neg*100:.1f}%)")

    # 3) 현재 우리 표본의 적정성 평가 (reviews.csv / analysis_v2.csv 동적 계산)
    import csv as _csv
    collected_pos = collected_neg = 0
    try:
        with open(cfg.REVIEWS_CSV,"r",encoding="utf-8-sig",newline="") as _f:
            for _r in _csv.DictReader(_f):
                if _r["voted_up"] == "1": collected_pos += 1
                else: collected_neg += 1
    except Exception: pass
    analyzed_n = 0
    try:
        with open(cfg.ANALYSIS_CSV,"r",encoding="utf-8-sig",newline="") as _f:
            analyzed_n = sum(1 for _ in _csv.DictReader(_f))
    except Exception: pass

    print(f"\n{'='*60}")
    print(f"🔎 현재 수집한 표본(추천 {collected_pos} / 비추천 {collected_neg}) 적정성 평가")
    print(f"{'='*60}")
    n_have = collected_pos + collected_neg
    e_actual = margin_of_error(n_have, N_all, p=0.5, z=Z_95)
    print(f"  수집량 n = {n_have}건 (분석량 {analyzed_n}건은 짧은 리뷰 제외 후)")
    print(f"  → 도달 오차한계: ±{e_actual:.2f}%p @ 95% 신뢰수준")
    print(f"  → 충족 기준: ±5%p → {'✅ 충족' if e_actual <= 5 else '❌ 부족'}")
    print(f"               ±3%p → {'✅ 충족' if e_actual <= 3 else '❌ 부족 (더 많이 수집해야)'}")

    print(f"\n  비율 비교:")
    have_r_pos = collected_pos / n_have if n_have else 0
    have_r_neg = collected_neg / n_have if n_have else 0
    print(f"     모집단:  추천 {r_pos*100:.1f}% / 비추천 {r_neg*100:.1f}%")
    print(f"     수집표본: 추천 {have_r_pos*100:.1f}% / 비추천 {have_r_neg*100:.1f}%")
    bias = (have_r_neg - r_neg) * 100
    if abs(bias) > 5:
        print(f"     → ⚠️ 비추천 표본을 {'+'+str(int(bias)) if bias>0 else str(int(bias))}%p **과대표집** (의도적 보강, 부정 인사이트 깊이 확보 목적)")
    else:
        print(f"     → ✅ 모집단 비율과 ±5%p 이내 일치")

    # 분석된 표본 기준으로도 평가
    e_analyzed = margin_of_error(analyzed_n, N_all, p=0.5, z=Z_95)
    print(f"\n  실제 분석된 {analyzed_n}건 기준:")
    print(f"     도달 오차한계: ±{e_analyzed:.2f}%p @ 95% 신뢰수준")
    print(f"     → 충족: ±5%p {'✅' if e_analyzed <= 5 else '❌'} / ±3%p {'✅' if e_analyzed <= 3 else '❌'}")

    out = {
        "population": {"total": N_all, "positive": N_pos, "negative": N_neg,
                       "pos_rate": r_pos, "neg_rate": r_neg, "score": score},
        "required_sample_sizes": {f"e_{p}pct": n for p, n in table},
        "stratified_recommendation": {
            "total": n_total_5pct,
            "positive": n_pos_target,
            "negative": n_neg_target,
        },
        "current_sample": {
            "collected": n_have, "analyzed": analyzed_n,
            "pos_collected": collected_pos, "neg_collected": collected_neg,
            "margin_of_error_collected_pct": round(e_actual, 2),
            "margin_of_error_analyzed_pct": round(e_analyzed, 2),
            "bias_neg_pct_overrepresented": round(bias, 1),
        },
    }
    with open(cfg.SAMPLE_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n✅ sample_design.json 저장")


if __name__ == "__main__":
    main()
