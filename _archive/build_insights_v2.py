"""v2 인사이트 집계 + 차트 (강의 표준: ABSA 6-Aspect / 감정 / 키워드 토픽)

입력 : analysis_v2.csv
출력 :
  - charts_v2/sentiment.png        : overall 감성 도넛
  - charts_v2/emotion.png          : 다차원 감정 막대 (강의 session-18)
  - charts_v2/aspects.png          : 6-Aspect 누적 막대 (강의 session-23)
  - charts_v2/topics.png           : 키워드 토픽 분포
  - charts_v2/mobile_impl.png      : 모바일 시사점 분포
  - charts_v2/playtime_bucket.png  : 플레이타임 구간별 추천률
  - insights_v2.json               : PDF에서 사용할 모든 수치/문구
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

COL_POS  = "#4CAF50"
COL_NEG  = "#E53935"
COL_NEU  = "#9E9E9E"
COL_MIX  = "#FB8C00"
COL_BLUE = "#1E88E5"

os.makedirs("charts_v2", exist_ok=True)

ASPECTS = ["graphics", "gameplay", "story", "performance", "value", "multiplayer"]
ASPECT_KR = {
    "graphics": "그래픽",
    "gameplay": "게임플레이",
    "story": "스토리",
    "performance": "성능·버그",
    "value": "가격·가성비",
    "multiplayer": "멀티플레이",
}
EMOTIONS = ["JOY", "SATISFACTION", "ANGER", "DISAPPOINTMENT", "BOREDOM", "SURPRISE", "NEUTRAL"]
EMOTION_KR = {
    "JOY": "기쁨",
    "SATISFACTION": "만족",
    "ANGER": "분노",
    "DISAPPOINTMENT": "실망",
    "BOREDOM": "지루함",
    "SURPRISE": "놀람",
    "NEUTRAL": "중립",
}
TOPICS = ["technical", "content", "value", "community", "other"]
TOPIC_KR = {
    "technical": "기술(버그·성능)",
    "content": "콘텐츠",
    "value": "가성비·가격",
    "community": "커뮤니티·멀티",
    "other": "기타",
}


def load_rows():
    rows = []
    with open("analysis_v2.csv", "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                r["voted_up"]   = int(r["voted_up"])
                r["playtime_h"] = float(r["playtime_h"])
            except Exception:
                continue
            kws = []
            for token in (r.get("keywords") or "").split("|"):
                if "@" in token:
                    w, t = token.split("@", 1)
                    if w: kws.append({"word": w.strip(), "topic": t.strip().lower()})
            r["keywords_parsed"] = kws
            rows.append(r)
    return rows


def chart_sentiment(rows):
    c = Counter(r["overall_sentiment"] for r in rows)
    labels = ["POSITIVE", "NEGATIVE", "MIXED", "NEUTRAL"]
    values = [c.get(k, 0) for k in labels]
    colors = [COL_POS, COL_NEG, COL_MIX, COL_NEU]
    kr = {"POSITIVE": "긍정", "NEGATIVE": "부정", "MIXED": "혼합", "NEUTRAL": "중립"}
    show_labels = [f"{kr[l]}\n{v}건" for l, v in zip(labels, values)]
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=140)
    ax.pie(values, labels=show_labels, colors=colors, autopct="%1.1f%%",
           startangle=90, wedgeprops=dict(width=0.42, edgecolor="white"))
    ax.set_title("전체 감성 분포 (Overall Sentiment)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    fig.savefig("charts_v2/sentiment.png", bbox_inches="tight")
    plt.close(fig)
    return dict(zip(labels, values))


def chart_emotion(rows):
    """다차원 감정 분류 (강의 session-18 패턴)"""
    c = Counter(r["emotion"] for r in rows)
    # 의미 있는 감정만, 빈도 큰 순
    items = [(e, c.get(e, 0)) for e in EMOTIONS if c.get(e, 0) > 0]
    items.sort(key=lambda x: -x[1])
    labels = [EMOTION_KR.get(e, e) for e, _ in items]
    values = [v for _, v in items]
    pos_emo = {"JOY", "SATISFACTION", "SURPRISE"}
    neg_emo = {"ANGER", "DISAPPOINTMENT", "BOREDOM"}
    colors = []
    for e, _ in items:
        if e in pos_emo: colors.append(COL_POS)
        elif e in neg_emo: colors.append(COL_NEG)
        else: colors.append(COL_NEU)

    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=140)
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("리뷰 수")
    ax.set_title("구체적 감정 분포 (ABSA 강의 패턴)", fontsize=12, fontweight="bold")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=9)
    plt.tight_layout()
    fig.savefig("charts_v2/emotion.png", bbox_inches="tight")
    plt.close(fig)
    return {e: c.get(e, 0) for e in EMOTIONS}


def chart_aspects(rows):
    """6-Aspect ABSA — POSITIVE/NEGATIVE/NEUTRAL 누적 막대 (강의 session-23 패턴)"""
    stats = {a: {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0, "NOT_MENTIONED": 0} for a in ASPECTS}
    for r in rows:
        for a in ASPECTS:
            s = (r.get(f"aspect_{a}_sentiment") or "NOT_MENTIONED").upper()
            if s not in stats[a]: s = "NOT_MENTIONED"
            stats[a][s] += 1

    labels = [ASPECT_KR[a] for a in ASPECTS]
    pos_vals = [stats[a]["POSITIVE"] for a in ASPECTS]
    neu_vals = [stats[a]["NEUTRAL"] for a in ASPECTS]
    neg_vals = [stats[a]["NEGATIVE"] for a in ASPECTS]
    nm_vals  = [stats[a]["NOT_MENTIONED"] for a in ASPECTS]

    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=140)
    ax.bar(labels, pos_vals, color=COL_POS, label="POSITIVE")
    ax.bar(labels, neu_vals, bottom=pos_vals, color=COL_NEU, label="NEUTRAL")
    bottom2 = [p+n for p, n in zip(pos_vals, neu_vals)]
    ax.bar(labels, neg_vals, bottom=bottom2, color=COL_NEG, label="NEGATIVE")
    ax.set_ylabel("리뷰 수")
    ax.set_title("ABSA 6-Aspect 감성 분포 (강의 표준)", fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", fontsize=9)

    for i, a in enumerate(ASPECTS):
        total_men = pos_vals[i] + neu_vals[i] + neg_vals[i]
        ax.text(i, total_men + 3, f"언급 {total_men}", ha="center", fontsize=8, color="#555")

    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    fig.savefig("charts_v2/aspects.png", bbox_inches="tight")
    plt.close(fig)

    # 부정 비율 우선순위 (강의 session-18 "개선 우선순위" 패턴)
    priority = []
    for a in ASPECTS:
        mentioned = stats[a]["POSITIVE"] + stats[a]["NEGATIVE"] + stats[a]["NEUTRAL"]
        if mentioned == 0: continue
        neg_rate = stats[a]["NEGATIVE"] / mentioned * 100
        priority.append({"aspect": a, "aspect_kr": ASPECT_KR[a],
                         "mentioned": mentioned,
                         "pos": stats[a]["POSITIVE"], "neg": stats[a]["NEGATIVE"],
                         "neu": stats[a]["NEUTRAL"], "neg_rate": neg_rate})
    priority.sort(key=lambda x: -x["neg_rate"])
    return {"stats": stats, "priority": priority}


def chart_topics(rows):
    c = Counter()
    for r in rows:
        for k in r["keywords_parsed"]:
            t = k["topic"] if k["topic"] in TOPICS else "other"
            c[t] += 1
    items = [(t, c.get(t, 0)) for t in TOPICS if c.get(t, 0) > 0]
    items.sort(key=lambda x: -x[1])
    labels = [TOPIC_KR[t] for t, _ in items]
    values = [v for _, v in items]
    palette = ["#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#9E9E9E"]
    colors = palette[:len(labels)]

    fig, ax = plt.subplots(figsize=(5.6, 3.6), dpi=140)
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("키워드 빈도")
    ax.set_title("키워드 토픽 분포 (강의 session-23)", fontsize=12, fontweight="bold")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=9)
    plt.tight_layout()
    fig.savefig("charts_v2/topics.png", bbox_inches="tight")
    plt.close(fig)
    return {t: c.get(t, 0) for t in TOPICS}


def chart_mobile_impl(rows):
    c = Counter(r["mobile_impl"] for r in rows if r["mobile_impl"])
    order = ["FIT", "NEEDS_REDESIGN", "UNFIT", "IRRELEVANT"]
    kr = {"FIT": "모바일 적합", "NEEDS_REDESIGN": "재설계 시 적합",
          "UNFIT": "모바일 부적합", "IRRELEVANT": "무관"}
    labels = [kr[k] for k in order if c.get(k, 0) > 0]
    values = [c[k] for k in order if c.get(k, 0) > 0]
    colors_map = {"모바일 적합": COL_POS, "재설계 시 적합": COL_MIX,
                  "모바일 부적합": COL_NEG, "무관": COL_NEU}
    colors = [colors_map[l] for l in labels]
    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=140)
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("리뷰 수")
    ax.set_title("모바일 이식 시사점 분포", fontsize=12, fontweight="bold")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width()/2, v + 1, str(v), ha="center", fontsize=10)
    plt.tight_layout()
    fig.savefig("charts_v2/mobile_impl.png", bbox_inches="tight")
    plt.close(fig)
    return {k: c.get(k, 0) for k in order}


def chart_playtime(rows):
    buckets = [("0~5h", 0, 5), ("5~25h", 5, 25), ("25~100h", 25, 100), ("100h+", 100, 10**9)]
    out, labels, rates, totals = {}, [], [], []
    for name, lo, hi in buckets:
        sub = [r for r in rows if lo <= r["playtime_h"] < hi]
        if not sub: continue
        rec = sum(1 for r in sub if r["voted_up"] == 1) / len(sub) * 100
        labels.append(name); rates.append(rec); totals.append(len(sub))
        out[name] = {"recommend_rate": rec, "n": len(sub)}
    fig, ax = plt.subplots(figsize=(6.0, 3.4), dpi=140)
    bars = ax.bar(labels, rates, color=COL_BLUE)
    ax.set_ylim(0, 105)
    ax.set_ylabel("추천률 (%)")
    ax.set_title("플레이타임 구간별 추천률", fontsize=12, fontweight="bold")
    for b, r, n in zip(bars, rates, totals):
        ax.text(b.get_x() + b.get_width()/2, r + 1.5, f"{r:.0f}%\n(n={n})", ha="center", fontsize=9)
    plt.tight_layout()
    fig.savefig("charts_v2/playtime_bucket.png", bbox_inches="tight")
    plt.close(fig)
    return out


def top_evidence(rows, aspect, sentiment, limit=4):
    """특정 aspect + sentiment의 evidence 인용 Top (중복 제거)"""
    out = []
    seen = set()
    for r in rows:
        s = (r.get(f"aspect_{aspect}_sentiment") or "").upper()
        if s != sentiment: continue
        ev = (r.get(f"aspect_{aspect}_evidence") or "").strip()
        if not ev or ev in seen: continue
        seen.add(ev)
        out.append(ev[:60])
        if len(out) >= limit: break
    return out


def top_key_phrases(rows, voted_filter, limit=8):
    cnt = Counter()
    for r in rows:
        if r["voted_up"] != voted_filter: continue
        p = (r.get("key_phrase") or "").strip()
        if len(p) >= 4: cnt[p] += 1
    return cnt.most_common(limit)


def top_keywords_by_topic(rows, topic, limit=6):
    cnt = Counter()
    for r in rows:
        for k in r["keywords_parsed"]:
            if k["topic"] == topic:
                w = k["word"].strip().lower()
                if w: cnt[w] += 1
    return cnt.most_common(limit)


def main():
    rows = load_rows()
    print(f"v2 분석 결과 {len(rows)}건 로드")

    sent       = chart_sentiment(rows)
    emo        = chart_emotion(rows)
    aspect_res = chart_aspects(rows)
    topic_dist = chart_topics(rows)
    mob        = chart_mobile_impl(rows)
    play       = chart_playtime(rows)

    # Evidence 인용 (강의 session-18 ABSA evidence)
    evidence = {a: {
        "positive": top_evidence(rows, a, "POSITIVE", 4),
        "negative": top_evidence(rows, a, "NEGATIVE", 4),
    } for a in ASPECTS}

    insights = {
        "n_total" : len(rows),
        "n_pos"   : sum(1 for r in rows if r["voted_up"] == 1),
        "n_neg"   : sum(1 for r in rows if r["voted_up"] == 0),
        "sentiment": sent,
        "emotion": emo,
        "aspects": aspect_res["stats"],
        "aspect_priority": aspect_res["priority"],
        "aspect_evidence": evidence,
        "topics": topic_dist,
        "mobile_impl": mob,
        "playtime": play,
        "top_phrases_pos": top_key_phrases(rows, 1, 8),
        "top_phrases_neg": top_key_phrases(rows, 0, 8),
        "keywords_tech":     top_keywords_by_topic(rows, "technical", 6),
        "keywords_content":  top_keywords_by_topic(rows, "content", 6),
        "keywords_value":    top_keywords_by_topic(rows, "value", 6),
        "keywords_comm":     top_keywords_by_topic(rows, "community", 6),
    }
    with open("insights_v2.json", "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print("✅ insights_v2.json 저장")
    print("✅ charts_v2/ 6개 차트 생성")


if __name__ == "__main__":
    main()
