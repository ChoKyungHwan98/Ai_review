"""v3 차트 — v2 인사이트 로직 그대로, 차트 스타일만 가독성 강화.

핵심 변경:
- DPI 140 → 180
- 차트 figure 크기 ↑
- x축 라벨 회전 + 폰트 크기 ↑ (10~11pt)
- 도넛 차트 라벨 위치 조정 (labeldistance, pctdistance)
- 막대 그래프 위 숫자 폰트 ↑
- y축 'リ뷰 수' 같은 회전 한글 명확히
- 막대 그래프 사이 여백 확보
- 색상 톤 부드럽게

입력: analysis_v2.csv → insights_v3.json + charts_v3/*
"""

import os, json, csv
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
if os.path.exists(FONT_PATH):
    font_manager.fontManager.addfont(FONT_PATH)
rcParams["font.family"] = "Malgun Gothic"
rcParams["axes.unicode_minus"] = False
rcParams["font.size"] = 10
rcParams["axes.titlesize"] = 12
rcParams["axes.titleweight"] = "bold"
rcParams["axes.labelsize"] = 10
rcParams["xtick.labelsize"] = 10
rcParams["ytick.labelsize"] = 9
rcParams["legend.fontsize"] = 9
rcParams["savefig.dpi"] = 180
rcParams["figure.dpi"] = 180

COL_POS = "#43A047"; COL_NEG = "#E53935"; COL_NEU = "#9E9E9E"
COL_MIX = "#FB8C00"; COL_BLUE = "#1976D2"; COL_PUR = "#8E24AA"
COL_BG  = "#FAFAFA"

os.makedirs("charts_v3", exist_ok=True)

ASPECTS = ["graphics", "gameplay", "story", "performance", "value", "multiplayer"]
ASPECT_KR = {"graphics":"그래픽","gameplay":"게임플레이","story":"스토리",
             "performance":"성능·버그","value":"가격·가성비","multiplayer":"멀티플레이"}
EMOTIONS = ["JOY","SATISFACTION","ANGER","DISAPPOINTMENT","BOREDOM","SURPRISE","NEUTRAL"]
EMOTION_KR = {"JOY":"기쁨","SATISFACTION":"만족","ANGER":"분노","DISAPPOINTMENT":"실망",
              "BOREDOM":"지루","SURPRISE":"놀람","NEUTRAL":"중립"}
TOPICS = ["technical","content","value","community","other"]
TOPIC_KR = {"technical":"기술(버그·성능)","content":"콘텐츠",
            "value":"가성비·가격","community":"커뮤니티·멀티","other":"기타"}


def load_rows():
    rows = []
    with open("analysis_v2.csv","r",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            try:
                r["voted_up"] = int(r["voted_up"])
                r["playtime_h"] = float(r["playtime_h"])
            except Exception:
                continue
            kws = []
            for token in (r.get("keywords") or "").split("|"):
                if "@" in token:
                    w,t = token.split("@",1)
                    if w: kws.append({"word":w.strip(),"topic":t.strip().lower()})
            r["keywords_parsed"] = kws
            rows.append(r)
    return rows


def fmt_pct(p):
    return f"{p*100:.1f}%"


def chart_sentiment(rows):
    c = Counter(r["overall_sentiment"] for r in rows)
    labels = ["POSITIVE","NEGATIVE","MIXED","NEUTRAL"]
    kr = {"POSITIVE":"긍정","NEGATIVE":"부정","MIXED":"혼합","NEUTRAL":"중립"}
    values = [c.get(k,0) for k in labels]
    # 0개 항목 제외
    keep = [(l,v) for l,v in zip(labels,values) if v>0]
    labels = [k[0] for k in keep]; values = [k[1] for k in keep]
    cmap = {"POSITIVE":COL_POS,"NEGATIVE":COL_NEG,"MIXED":COL_MIX,"NEUTRAL":COL_NEU}
    colors = [cmap[l] for l in labels]

    fig, ax = plt.subplots(figsize=(5.5,5.0), dpi=180)
    wedges, _ = ax.pie(values, colors=colors, startangle=90,
                       wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
                       labels=None)
    # 가운데 텍스트
    total = sum(values)
    ax.text(0,0.05,f"{total}건", ha="center", va="center", fontsize=18, fontweight="bold")
    ax.text(0,-0.18,"분석 리뷰", ha="center", va="center", fontsize=10, color="#666")

    # 범례 (라벨 겹침 회피)
    legend_lbls = [f"{kr[l]} {v}건 ({v/total*100:.1f}%)" for l,v in zip(labels,values)]
    ax.legend(wedges, legend_lbls, loc="center left",
              bbox_to_anchor=(1.0, 0.5), frameon=False)

    ax.set_title("전체 감성 분포", pad=10)
    plt.tight_layout()
    fig.savefig("charts_v3/sentiment.png", bbox_inches="tight")
    plt.close(fig)
    return {l:c.get(l,0) for l in ["POSITIVE","NEGATIVE","MIXED","NEUTRAL"]}


def chart_emotion(rows):
    c = Counter(r["emotion"] for r in rows)
    items = [(e,c.get(e,0)) for e in EMOTIONS if c.get(e,0)>0]
    items.sort(key=lambda x:-x[1])
    labels = [EMOTION_KR.get(e,e) for e,_ in items]
    values = [v for _,v in items]
    pos_set = {"JOY","SATISFACTION","SURPRISE"}
    neg_set = {"ANGER","DISAPPOINTMENT","BOREDOM"}
    colors = [COL_POS if e in pos_set else (COL_NEG if e in neg_set else COL_NEU)
              for e,_ in items]

    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=180)
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=1, width=0.6)
    ax.set_ylabel("리뷰 수", labelpad=8)
    ax.set_title("구체적 감정 분포 (다차원 감정 분류 — 강의 session-18)")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelrotation=0)
    max_v = max(values) if values else 1
    for b,v in zip(bars,values):
        ax.text(b.get_x()+b.get_width()/2, v+max_v*0.02, str(v), ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0, max_v*1.18)
    plt.tight_layout()
    fig.savefig("charts_v3/emotion.png", bbox_inches="tight")
    plt.close(fig)
    return {e:c.get(e,0) for e in EMOTIONS}


def chart_aspects(rows):
    stats = {a:{"POSITIVE":0,"NEGATIVE":0,"NEUTRAL":0,"NOT_MENTIONED":0} for a in ASPECTS}
    for r in rows:
        for a in ASPECTS:
            s = (r.get(f"aspect_{a}_sentiment") or "NOT_MENTIONED").upper()
            if s not in stats[a]: s = "NOT_MENTIONED"
            stats[a][s] += 1

    labels = [ASPECT_KR[a] for a in ASPECTS]
    pos = [stats[a]["POSITIVE"] for a in ASPECTS]
    neu = [stats[a]["NEUTRAL"]  for a in ASPECTS]
    neg = [stats[a]["NEGATIVE"] for a in ASPECTS]

    fig, ax = plt.subplots(figsize=(9.0, 4.6), dpi=180)
    width = 0.55
    bars1 = ax.bar(labels, pos, width=width, color=COL_POS, label="POSITIVE")
    bars2 = ax.bar(labels, neu, width=width, bottom=pos, color=COL_NEU, label="NEUTRAL")
    bottom = [p+n for p,n in zip(pos,neu)]
    bars3 = ax.bar(labels, neg, width=width, bottom=bottom, color=COL_NEG, label="NEGATIVE")
    ax.set_ylabel("리뷰 수", labelpad=8)
    ax.set_title("ABSA 6-Aspect 감성 분포 (강의 session-23 표준)")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.legend(loc="upper right", framealpha=0.95)

    # 막대 끝 위에 총 언급량 + 부정률
    for i, a in enumerate(ASPECTS):
        mentioned = pos[i] + neu[i] + neg[i]
        if mentioned == 0: continue
        neg_rate = neg[i]/mentioned*100
        ax.text(i, mentioned+max(pos)*0.03,
                f"언급 {mentioned}\n부정 {neg_rate:.0f}%",
                ha="center", fontsize=9, color="#333")

    plt.xticks(rotation=12, ha="right")
    plt.tight_layout()
    fig.savefig("charts_v3/aspects.png", bbox_inches="tight")
    plt.close(fig)

    priority = []
    for a in ASPECTS:
        mentioned = stats[a]["POSITIVE"]+stats[a]["NEGATIVE"]+stats[a]["NEUTRAL"]
        if mentioned == 0: continue
        priority.append({"aspect":a,"aspect_kr":ASPECT_KR[a],
                         "mentioned":mentioned,
                         "pos":stats[a]["POSITIVE"],"neg":stats[a]["NEGATIVE"],
                         "neu":stats[a]["NEUTRAL"],
                         "neg_rate": stats[a]["NEGATIVE"]/mentioned*100})
    priority.sort(key=lambda x:-x["neg_rate"])
    return {"stats":stats,"priority":priority}


def chart_topics(rows):
    c = Counter()
    for r in rows:
        for k in r["keywords_parsed"]:
            t = k["topic"] if k["topic"] in TOPICS else "other"
            c[t] += 1
    items = [(t,c.get(t,0)) for t in TOPICS if c.get(t,0)>0]
    items.sort(key=lambda x:-x[1])
    labels = [TOPIC_KR[t] for t,_ in items]
    values = [v for _,v in items]
    palette = [COL_BLUE, COL_POS, COL_MIX, COL_PUR, COL_NEU]
    colors = palette[:len(labels)]

    fig, ax = plt.subplots(figsize=(7.0, 3.8), dpi=180)
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=1, height=0.55)
    ax.set_xlabel("키워드 빈도")
    ax.set_title("키워드 토픽 분포 (강의 session-23)")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.invert_yaxis()
    max_v = max(values) if values else 1
    for b,v in zip(bars,values):
        ax.text(v + max_v*0.02, b.get_y()+b.get_height()/2, str(v), va="center", fontsize=10, fontweight="bold")
    ax.set_xlim(0, max_v*1.15)
    plt.tight_layout()
    fig.savefig("charts_v3/topics.png", bbox_inches="tight")
    plt.close(fig)
    return {t:c.get(t,0) for t in TOPICS}


def chart_mobile_impl(rows):
    c = Counter(r["mobile_impl"] for r in rows if r["mobile_impl"])
    order = ["FIT","NEEDS_REDESIGN","UNFIT","IRRELEVANT"]
    kr = {"FIT":"모바일 적합","NEEDS_REDESIGN":"재설계 시 적합","UNFIT":"모바일 부적합","IRRELEVANT":"무관"}
    labels = [kr[k] for k in order if c.get(k,0)>0]
    values = [c[k] for k in order if c.get(k,0)>0]
    cmap = {"모바일 적합":COL_POS,"재설계 시 적합":COL_MIX,"모바일 부적합":COL_NEG,"무관":COL_NEU}
    colors = [cmap[l] for l in labels]

    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=180)
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=1, width=0.55)
    ax.set_ylabel("리뷰 수", labelpad=8)
    ax.set_title("모바일 이식 시사점 분포")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    max_v = max(values) if values else 1
    for b,v in zip(bars,values):
        ax.text(b.get_x()+b.get_width()/2, v+max_v*0.02, str(v), ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0, max_v*1.18)
    plt.tight_layout()
    fig.savefig("charts_v3/mobile_impl.png", bbox_inches="tight")
    plt.close(fig)
    return {k:c.get(k,0) for k in order}


def chart_playtime(rows):
    buckets = [("0~5h",0,5),("5~25h",5,25),("25~100h",25,100),("100h+",100,10**9)]
    out, labels, rates, totals = {},[],[],[]
    for name,lo,hi in buckets:
        sub = [r for r in rows if lo <= r["playtime_h"] < hi]
        if not sub: continue
        rec = sum(1 for r in sub if r["voted_up"]==1)/len(sub)*100
        labels.append(name); rates.append(rec); totals.append(len(sub))
        out[name] = {"recommend_rate":rec,"n":len(sub)}

    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=180)
    bars = ax.bar(labels, rates, color=COL_BLUE, edgecolor="white", linewidth=1, width=0.55)
    ax.set_ylim(0,108)
    ax.set_ylabel("추천률 (%)", labelpad=8)
    ax.set_title("플레이타임 구간별 추천률 (이탈 위험 구간 진단)")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for b,r_,n in zip(bars,rates,totals):
        ax.text(b.get_x()+b.get_width()/2, r_+2,
                f"{r_:.0f}%\n(n={n})", ha="center", fontsize=10, fontweight="bold")
    plt.tight_layout()
    fig.savefig("charts_v3/playtime.png", bbox_inches="tight")
    plt.close(fig)
    return out


def chart_timeline(rows):
    """시계열 추이 (강의 session-27) — 분석 데이터에 timestamp 없으니 reviews.csv 매핑"""
    # reviews.csv에서 timestamp 가져오기
    ts_map = {}
    with open("reviews.csv","r",encoding="utf-8-sig",newline="") as f:
        for rv in csv.DictReader(f):
            try:
                ts_map[rv["recommendationid"]] = int(rv["timestamp_created"])
            except Exception:
                pass
    import datetime
    by_month = {}  # YYYY-MM -> {"pos":x,"neg":y,"total":z}
    for r in rows:
        ts = ts_map.get(r["recommendationid"])
        if not ts: continue
        ym = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
        d = by_month.setdefault(ym, {"pos":0,"neg":0,"total":0})
        if r["voted_up"]==1: d["pos"] += 1
        else: d["neg"] += 1
        d["total"] += 1
    # 정렬, 최근 12개월만
    months = sorted(by_month.keys())[-12:]
    if len(months) < 2:
        return {}
    rates = [by_month[m]["pos"]/by_month[m]["total"]*100 if by_month[m]["total"]>0 else 0 for m in months]
    totals = [by_month[m]["total"] for m in months]

    fig, ax = plt.subplots(figsize=(9.0, 3.8), dpi=180)
    ax.plot(months, rates, marker="o", color=COL_BLUE, linewidth=2, markersize=7)
    ax.set_ylim(0, 108)
    ax.set_ylabel("추천률 (%)", labelpad=8)
    ax.set_title("월별 추천률 추이 (시계열 — 강의 session-27)")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for x,y,n in zip(months,rates,totals):
        ax.annotate(f"{y:.0f}%\n(n={n})", (x,y), textcoords="offset points",
                    xytext=(0,10), ha="center", fontsize=8)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig("charts_v3/timeline.png", bbox_inches="tight")
    plt.close(fig)
    return {m: {"recommend_rate":by_month[m]["pos"]/by_month[m]["total"]*100 if by_month[m]["total"]>0 else 0,
                "n":by_month[m]["total"]} for m in months}


def top_evidence(rows, aspect, sentiment, limit=4):
    out, seen = [], set()
    for r in rows:
        s = (r.get(f"aspect_{aspect}_sentiment") or "").upper()
        if s != sentiment: continue
        ev = (r.get(f"aspect_{aspect}_evidence") or "").strip()
        if not ev or ev in seen: continue
        seen.add(ev); out.append(ev[:60])
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
    print(f"v3 분석 결과 {len(rows)}건 로드")

    sent = chart_sentiment(rows)
    emo  = chart_emotion(rows)
    asp  = chart_aspects(rows)
    top  = chart_topics(rows)
    mob  = chart_mobile_impl(rows)
    play = chart_playtime(rows)
    timeline = chart_timeline(rows)

    evidence = {a: {
        "positive": top_evidence(rows, a, "POSITIVE", 4),
        "negative": top_evidence(rows, a, "NEGATIVE", 4),
    } for a in ASPECTS}

    insights = {
        "n_total": len(rows),
        "n_pos": sum(1 for r in rows if r["voted_up"]==1),
        "n_neg": sum(1 for r in rows if r["voted_up"]==0),
        "sentiment": sent, "emotion": emo,
        "aspects": asp["stats"], "aspect_priority": asp["priority"],
        "aspect_evidence": evidence,
        "topics": top, "mobile_impl": mob, "playtime": play, "timeline": timeline,
        "top_phrases_pos": top_key_phrases(rows, 1, 8),
        "top_phrases_neg": top_key_phrases(rows, 0, 8),
        "keywords_tech":    top_keywords_by_topic(rows, "technical", 6),
        "keywords_content": top_keywords_by_topic(rows, "content", 6),
        "keywords_value":   top_keywords_by_topic(rows, "value", 6),
        "keywords_comm":    top_keywords_by_topic(rows, "community", 6),
    }
    with open("insights_v3.json", "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)
    print("✅ insights_v3.json + charts_v3/ 생성")


if __name__ == "__main__":
    main()
