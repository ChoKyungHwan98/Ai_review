"""인사이트 집계 + 차트 + 분석서 본문(JSON) 생성

입력 : analysis.csv, reviews.csv
출력 :
  - charts/sentiment.png       : 감성 비율 (도넛)
  - charts/categories.png      : 카테고리별 언급량 (가로 막대)
  - charts/mobile_impl.png     : 모바일 시사점 분포
  - charts/playtime_bucket.png : 플레이타임 구간별 추천률
  - insights.json              : 분석서 본문에 들어갈 모든 수치/문구

한글 폰트는 Windows '맑은 고딕' 사용.
"""

import os
import json
import csv
from collections import Counter, defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---- 한글 폰트 ----
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
    plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# ---- 색상 ----
COL_POS  = "#4CAF50"
COL_NEG  = "#E53935"
COL_NEU  = "#9E9E9E"
COL_BLUE = "#1E88E5"
COL_ORG  = "#FB8C00"

os.makedirs("charts", exist_ok=True)


def load_rows():
    rows = []
    with open("analysis.csv", "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                r["voted_up"]  = int(r["voted_up"])
                r["playtime_h"] = float(r["playtime_h"])
            except Exception:
                continue
            r["categories"]  = [c for c in (r["categories"] or "").split("|") if c]
            r["main_points"] = [p for p in (r["main_points"] or "").split("|") if p]
            rows.append(r)
    return rows


def chart_sentiment(rows):
    c = Counter(r["sentiment"] for r in rows)
    labels = ["긍정", "부정", "중립"]
    values = [c.get(k, 0) for k in labels]
    colors = [COL_POS, COL_NEG, COL_NEU]
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=140)
    ax.pie(values, labels=[f"{l}\n{v}건" for l, v in zip(labels, values)],
           colors=colors, autopct="%1.1f%%", startangle=90,
           wedgeprops=dict(width=0.42, edgecolor="white"))
    ax.set_title("감성 분포 (LLM 분류)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig("charts/sentiment.png", bbox_inches="tight")
    plt.close(fig)
    return dict(zip(labels, values))


def chart_categories(rows):
    cnt = Counter()
    pos_cnt = Counter()
    neg_cnt = Counter()
    for r in rows:
        for c in r["categories"]:
            cnt[c] += 1
            if r["voted_up"] == 1:
                pos_cnt[c] += 1
            else:
                neg_cnt[c] += 1
    top = cnt.most_common(10)
    if not top:
        return {}
    labels = [k for k, _ in top][::-1]
    pos_vals = [pos_cnt[l] for l in labels]
    neg_vals = [neg_cnt[l] for l in labels]
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=140)
    ax.barh(labels, pos_vals, color=COL_POS, label="추천 리뷰에서 언급")
    ax.barh(labels, neg_vals, left=pos_vals, color=COL_NEG, label="비추천 리뷰에서 언급")
    ax.set_xlabel("언급 횟수")
    ax.set_title("카테고리별 언급량 (Top 10)", fontsize=12, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    for i, l in enumerate(labels):
        total = pos_vals[i] + neg_vals[i]
        ax.text(total + 1, i, str(total), va="center", fontsize=9)
    plt.tight_layout()
    fig.savefig("charts/categories.png", bbox_inches="tight")
    plt.close(fig)
    return {l: {"pos": pos_cnt[l], "neg": neg_cnt[l], "total": cnt[l]} for l in cnt}


def chart_mobile_impl(rows):
    c = Counter(r["mobile_impl"] for r in rows if r["mobile_impl"])
    order = ["모바일적합", "모바일에서개선가능", "모바일부적합", "무관"]
    labels = [k for k in order if c.get(k, 0) > 0]
    values = [c[k] for k in labels]
    colors_map = {"모바일적합": COL_POS, "모바일에서개선가능": COL_ORG,
                  "모바일부적합": COL_NEG, "무관": COL_NEU}
    colors = [colors_map[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=140)
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("언급 리뷰 수")
    ax.set_title("모바일 이식 시사점 분포", fontsize=12, fontweight="bold")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=10)
    plt.tight_layout()
    fig.savefig("charts/mobile_impl.png", bbox_inches="tight")
    plt.close(fig)
    return dict(zip(labels, values))


def chart_playtime(rows):
    buckets = [("0~5h", 0, 5), ("5~25h", 5, 25), ("25~100h", 25, 100), ("100h+", 100, 10**9)]
    out = {}
    labels, rates, totals = [], [], []
    for name, lo, hi in buckets:
        sub = [r for r in rows if lo <= r["playtime_h"] < hi]
        if not sub:
            continue
        rec = sum(1 for r in sub if r["voted_up"] == 1) / len(sub) * 100
        labels.append(name); rates.append(rec); totals.append(len(sub))
        out[name] = {"recommend_rate": rec, "n": len(sub)}
    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=140)
    bars = ax.bar(labels, rates, color=COL_BLUE)
    ax.set_ylim(0, 105)
    ax.set_ylabel("추천률 (%)")
    ax.set_title("플레이타임 구간별 추천률", fontsize=12, fontweight="bold")
    for b, r, n in zip(bars, rates, totals):
        ax.text(b.get_x() + b.get_width()/2, r + 1.5, f"{r:.0f}%\n(n={n})",
                ha="center", fontsize=9)
    plt.tight_layout()
    fig.savefig("charts/playtime_bucket.png", bbox_inches="tight")
    plt.close(fig)
    return out


def top_points(rows, voted_filter):
    """추천/비추천 별 핵심 포인트 빈도 Top"""
    cnt = Counter()
    for r in rows:
        if r["voted_up"] != voted_filter:
            continue
        for p in r["main_points"]:
            p = p.strip()
            if len(p) >= 4:
                cnt[p] += 1
    return cnt.most_common(15)


def top_negative_reasons(rows):
    """비추천 리뷰의 모바일 시사점 사유 Top"""
    cnt = Counter()
    for r in rows:
        if r["voted_up"] == 0 and r["mobile_reason"]:
            cnt[r["mobile_reason"]] += 1
    return cnt.most_common(15)


def main():
    rows = load_rows()
    print(f"분석 결과 {len(rows)}건 로드")
    sent_dist  = chart_sentiment(rows)
    cat_dist   = chart_categories(rows)
    mob_dist   = chart_mobile_impl(rows)
    play_dist  = chart_playtime(rows)

    insights = {
        "n_total"   : len(rows),
        "n_pos"     : sum(1 for r in rows if r["voted_up"] == 1),
        "n_neg"     : sum(1 for r in rows if r["voted_up"] == 0),
        "sentiment" : sent_dist,
        "categories": cat_dist,
        "mobile_impl": mob_dist,
        "playtime"  : play_dist,
        "top_points_positive" : top_points(rows, 1),
        "top_points_negative" : top_points(rows, 0),
        "negative_mobile_reasons": top_negative_reasons(rows),
    }
    with open("insights.json", "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print(f"✅ 인사이트 저장 → insights.json")
    print(f"✅ 차트 4개 저장 → charts/")


if __name__ == "__main__":
    main()
