"""v2 A4 2장 PDF 생성 — 강의 session-31 표준 5부 구조

5부 구조 (강의 session-31 정확히):
  1) Executive Summary  (한 줄 요약)
  2) Current State      (현황 2-3 문장)
  3) Key Findings       (핵심 발견 3가지, finding + impact)
  4) Recommendations    (권장 조치 P1/P2/P3 — priority + action + reason)
  5) Expected Impact    (기대 효과 정량 목표)
  + Limitations         (분석 한계점)

핵심 데이터 시각화:
- 페이지 1: 전체 감성 도넛 + ABSA 6-Aspect 막대 + 다차원 감정 막대 + KPI + Key Findings
- 페이지 2: 모바일 시사점 + 플레이타임 + 키워드 토픽 + Recommendations + Limitations
"""

import os, json
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
)

pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBold", "C:/Windows/Fonts/malgunbd.ttf"))

C_POS  = colors.HexColor("#2E7D32")
C_NEG  = colors.HexColor("#C62828")
C_MIX  = colors.HexColor("#EF6C00")
C_BG   = colors.HexColor("#F4F6F8")
C_DARK = colors.HexColor("#212121")
C_GRAY = colors.HexColor("#5F6368")
C_BLUE = colors.HexColor("#1565C0")
C_LINE = colors.HexColor("#E0E0E0")


def styles():
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=s["Normal"], fontName="MalgunBold",
                                fontSize=14.5, leading=17, textColor=C_DARK),
        "sub":   ParagraphStyle("sub", parent=s["Normal"], fontName="Malgun",
                                fontSize=8.2, leading=10, textColor=C_GRAY),
        "h2":    ParagraphStyle("h2", parent=s["Normal"], fontName="MalgunBold",
                                fontSize=10.5, leading=13, textColor=C_BLUE, spaceBefore=3, spaceAfter=2),
        "body":  ParagraphStyle("body", parent=s["Normal"], fontName="Malgun",
                                fontSize=8.4, leading=11, textColor=C_DARK),
        "small": ParagraphStyle("small", parent=s["Normal"], fontName="Malgun",
                                fontSize=7.5, leading=9.5, textColor=C_DARK),
        "bullet":ParagraphStyle("bullet", parent=s["Normal"], fontName="Malgun",
                                fontSize=8.3, leading=11, leftIndent=8, textColor=C_DARK),
        "kpi_label": ParagraphStyle("kpi_label", parent=s["Normal"], fontName="Malgun",
                                    fontSize=7.2, leading=8.5, textColor=C_GRAY, alignment=TA_CENTER),
        "kpi_val":   ParagraphStyle("kpi_val", parent=s["Normal"], fontName="MalgunBold",
                                    fontSize=14, leading=16, alignment=TA_CENTER, textColor=C_DARK),
        "exec":  ParagraphStyle("exec", parent=s["Normal"], fontName="Malgun",
                                fontSize=9, leading=12.5, textColor=C_DARK, leftIndent=4),
        "footer":ParagraphStyle("footer", parent=s["Normal"], fontName="Malgun",
                                fontSize=6.8, leading=8, textColor=C_GRAY, alignment=TA_LEFT),
    }


def kpi_card(label, value, color, st, w=43*mm):
    inner = Table(
        [[Paragraph(label, st["kpi_label"])],
         [Paragraph(f'<font color="{color.hexval()}">{value}</font>', st["kpi_val"])]],
        colWidths=[w], rowHeights=[6*mm, 11*mm]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, C_LINE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
    ]))
    return inner


def boxed_block(title, body_paragraphs, color, st, width):
    rows = [[Paragraph(f'<font color="{color.hexval()}"><b>{title}</b></font>', st["h2"])]]
    for p in body_paragraphs:
        rows.append([p])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, C_LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return t


# ====================================================================
# 데이터 → 강의 표준 인사이트 도출 (session-31 패턴)
# ====================================================================

def derive_key_findings(ins):
    """3가지 핵심 발견 (finding + impact)"""
    findings = []

    # ① ABSA 부정 비율 최고 영역
    pri = ins.get("aspect_priority", [])
    if pri:
        worst = pri[0]
        findings.append({
            "type": "최우선 개선 영역",
            "finding": f"6-Aspect 중 '{worst['aspect_kr']}'의 부정 비율 <b>{worst['neg_rate']:.0f}%</b> (언급 {worst['mentioned']}회 · 부정 {worst['neg']}건)",
            "impact": "한국 유저 비추천의 1순위 사유. 모바일에서 동일 문제 발생 시 출시 직후 부정 리뷰 폭주 위험",
        })

    # ② 감정 분포 (강의 session-18 통찰)
    emo = ins.get("emotion", {})
    disappointment = emo.get("DISAPPOINTMENT", 0)
    anger = emo.get("ANGER", 0)
    boredom = emo.get("BOREDOM", 0)
    if disappointment + anger + boredom > 0:
        if disappointment > anger:
            tag = "DISAPPOINTMENT(실망)"; n = disappointment
            impact = "기대치 대비 미달 — 콘텐츠/완성도 보강만으로도 회복 가능. 분노보다 다루기 쉬움"
        elif anger > 0:
            tag = "ANGER(분노)"; n = anger
            impact = "환불·악평 위험. 모바일 출시 시 CS 응대 시나리오 사전 준비 + 핫픽스 라인 필수"
        else:
            tag = "BOREDOM(지루함)"; n = boredom
            impact = "엔드게임/콘텐츠 깊이 부족 — 모바일에서 짧은 세션이라도 진행감을 끊임없이 제공해야 이탈 방지"
        findings.append({
            "type": "비추천 유저의 주된 감정",
            "finding": f"가장 빈도 높은 부정 감정은 <b>{tag} {n}건</b>",
            "impact": impact,
        })

    # ③ 플레이타임 곡선의 함정
    play = ins.get("playtime", {})
    if play:
        # 가장 낮은 추천률 구간
        worst_bucket = min(play.items(), key=lambda x: x[1]["recommend_rate"])
        coreset = play.get("100h+", {})
        if worst_bucket and coreset:
            findings.append({
                "type": "이탈 위험 구간",
                "finding": f"플레이타임 <b>{worst_bucket[0]}</b> 구간 추천률 <b>{worst_bucket[1]['recommend_rate']:.0f}%</b> (최저), 코어({coreset.get('n',0)}명, 100h+) <b>{coreset.get('recommend_rate', 0):.0f}%</b>",
                "impact": f"모바일은 짧은 세션이 본질 — {worst_bucket[0]} 구간을 못 넘기면 PC보다 더 빠르게 이탈. 1주차 온보딩 설계가 성공 변수",
            })

    return findings[:3]


def derive_recommendations(ins):
    """P1/P2/P3 권장 조치 — priority + action + reason (session-31 표준)"""
    recs = []
    pri = ins.get("aspect_priority", [])
    mob = ins.get("mobile_impl", {})
    aspects = ins.get("aspects", {})

    # P1: 최우선 회피·개선 영역
    if pri:
        worst = pri[0]
        evidence_neg = (ins.get("aspect_evidence", {}).get(worst["aspect"], {}).get("negative") or [])
        ev_text = ""
        if evidence_neg:
            ev_text = f' 근거 인용: <font color="#777777">"{evidence_neg[0][:50]}"</font>'
        recs.append({
            "priority": 1,
            "action": f"<b>{worst['aspect_kr']} 안정성 확보</b> — 모바일 출시 전 QA 예산 1.5~2배 책정",
            "reason": f"PC 한국 유저의 비추천 1순위(부정률 {worst['neg_rate']:.0f}%). 모바일은 디바이스 다양성으로 더 악화 가능.{ev_text}",
        })

    # P2: 강점 유지·강화
    # POSITIVE 비율이 가장 높은 aspect 찾기
    strongest = None
    best_pos = 0
    for a_name, a_stats in aspects.items():
        if a_stats["POSITIVE"] > best_pos:
            best_pos = a_stats["POSITIVE"]
            strongest = a_name
    if strongest:
        kr_map = {"graphics":"그래픽", "gameplay":"게임플레이", "story":"스토리",
                  "performance":"성능·버그", "value":"가격·가성비", "multiplayer":"멀티플레이"}
        evidence_pos = (ins.get("aspect_evidence", {}).get(strongest, {}).get("positive") or [])
        ev_text = ""
        if evidence_pos:
            ev_text = f' 근거 인용: <font color="#777777">"{evidence_pos[0][:50]}"</font>'
        recs.append({
            "priority": 2,
            "action": f"<b>{kr_map.get(strongest, strongest)} 강점을 모바일에서도 핵심 경험 축으로 유지</b>",
            "reason": f"한국 유저 호평 최다 영역(POSITIVE {best_pos}건). 모바일에서 축소되면 IP 정체성 손실.{ev_text}",
        })

    # P3: 모바일 재설계 기회
    redesign = mob.get("NEEDS_REDESIGN", 0)
    fit = mob.get("FIT", 0)
    unfit = mob.get("UNFIT", 0)
    total_mob = fit + redesign + unfit
    if total_mob > 0:
        ratio = (fit + redesign) / total_mob * 100
        recs.append({
            "priority": 3,
            "action": f"<b>'재설계 시 적합' {redesign}건의 영역을 모바일 네이티브로 재구성</b>",
            "reason": f"전체 모바일 적합도 의견 {total_mob}건 중 {ratio:.0f}%가 '적합/재설계 시 적합'. 단순 포팅이 아닌 모바일 폼팩터 재설계로 시장 확장 가능"
        })

    return recs[:3]


def derive_expected_impact(ins):
    """기대 효과 정량 목표"""
    pri = ins.get("aspect_priority", [])
    fit = ins.get("mobile_impl", {}).get("FIT", 0)
    redesign = ins.get("mobile_impl", {}).get("NEEDS_REDESIGN", 0)

    targets = []
    if pri and len(pri) >= 1:
        worst = pri[0]
        target_rate = max(15, int(worst["neg_rate"]) - 30)
        targets.append(f"<b>{worst['aspect_kr']}</b> 부정 비율을 {worst['neg_rate']:.0f}% → <b>{target_rate}%대</b>로 감축")
    if fit + redesign > 0:
        targets.append(f"모바일 친화 영역({fit + redesign}건) 우선 구현으로 출시 후 8주차 D30 유지율 <b>업계 평균 +5~10%p</b> 달성")
    targets.append("출시 30일 내 한국 유저 추천률 <b>70%</b> 이상 (PC 기준선)")
    return targets


# ====================================================================
# Main: PDF 생성
# ====================================================================

def make_report():
    with open("insights_v2.json", "r", encoding="utf-8") as f:
        ins = json.load(f)

    st = styles()
    doc = SimpleDocTemplate(
        "팰월드_스팀리뷰_분석서_v2.pdf",
        pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=11*mm, bottomMargin=9*mm,
    )
    story = []

    n_total = ins["n_total"]
    n_pos = ins["n_pos"]
    n_neg = ins["n_neg"]
    pos_pct = n_pos / n_total * 100 if n_total else 0

    # ============ 헤더 ============
    title_html = ('<font color="#1565C0">PC 스팀 팰월드(Palworld)</font>'
                  ' 한국 유저 리뷰 분석 — 모바일 이식 시사점')
    story.append(Paragraph(title_html, st["title"]))
    sub_html = (f"분석 대상: 최신 한국어 리뷰 {n_total}건 (추천 {n_pos} · 비추천 {n_neg}, 비추천 표본 보강 수집) | "
                f"방법: Steam Storefront API → 자체 FastAPI+SQLite 적재 → "
                f"Google Gemini 2.0 Flash로 ABSA 6-Aspect·다차원 감정·키워드 토픽·모바일 시사점 4축 멀티태스크 분석 | "
                f"작성: 조경환 · {date.today().isoformat()}")
    story.append(Paragraph(sub_html, st["sub"]))
    story.append(Spacer(1, 3))

    # ============ 1. EXECUTIVE SUMMARY ============
    pri = ins.get("aspect_priority", [])
    worst_kr = pri[0]["aspect_kr"] if pri else "성능·버그"
    worst_rate = pri[0]["neg_rate"] if pri else 0
    aspects = ins.get("aspects", {})
    # 가장 호평 영역
    best_aspect_kr = "게임플레이"
    best_pos = 0
    for a, s in aspects.items():
        if s["POSITIVE"] > best_pos:
            best_pos = s["POSITIVE"]
            kr_map = {"graphics":"그래픽", "gameplay":"게임플레이", "story":"스토리",
                      "performance":"성능·버그", "value":"가격·가성비", "multiplayer":"멀티플레이"}
            best_aspect_kr = kr_map.get(a, a)

    exec_html = (f"한국 유저 추천률 <b>{pos_pct:.0f}%</b>. 핵심 호평은 <b>{best_aspect_kr}</b>({best_pos}건), "
                 f"핵심 혹평은 <b>{worst_kr}</b>(부정률 {worst_rate:.0f}%). "
                 f"<b>모바일 이식 성공의 결정 변수는 호평 축을 유지하면서 {worst_kr} 안정성 확보 + 초기 이탈 구간의 온보딩 재설계.</b>")
    story.append(boxed_block("① Executive Summary", [Paragraph(exec_html, st["exec"])],
                              C_BLUE, st, 182*mm))
    story.append(Spacer(1, 4))

    # ============ KPI 4장 ============
    sent = ins["sentiment"]
    kpis = [
        kpi_card("총 분석 리뷰", f"{n_total}건", C_DARK, st),
        kpi_card("추천 비율", f"{pos_pct:.0f}%", C_POS, st),
        kpi_card("긍정 분류 (LLM)", f"{sent.get('POSITIVE',0)}건", C_POS, st),
        kpi_card("부정 분류 (LLM)", f"{sent.get('NEGATIVE',0)}건", C_NEG, st),
    ]
    kpi_row = Table([kpis], colWidths=[45*mm]*4, hAlign="CENTER")
    kpi_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(kpi_row)
    story.append(Spacer(1, 4))

    # ============ 2. CURRENT STATE — 차트 3개 ============
    chart_row = Table(
        [[Image("charts_v2/sentiment.png", width=58*mm, height=52*mm),
          Image("charts_v2/aspects.png",   width=120*mm, height=52*mm)]],
        colWidths=[60*mm, 122*mm], hAlign="CENTER"
    )
    chart_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row)
    story.append(Spacer(1, 3))

    # 감정 차트 (강의 session-18)
    chart_row2 = Table(
        [[Image("charts_v2/emotion.png", width=110*mm, height=42*mm),
          Image("charts_v2/topics.png",  width=70*mm,  height=42*mm)]],
        colWidths=[112*mm, 70*mm], hAlign="CENTER"
    )
    chart_row2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row2)
    story.append(Spacer(1, 4))

    # ============ 3. KEY FINDINGS ============
    findings = derive_key_findings(ins)
    finding_paras = []
    for i, f in enumerate(findings, 1):
        finding_paras.append(Paragraph(
            f'<b>{i}. {f["type"]}</b><br/>'
            f'• 발견: {f["finding"]}<br/>'
            f'• 의미: <font color="#444">{f["impact"]}</font>',
            st["body"]
        ))
        finding_paras.append(Spacer(1, 2))
    story.append(boxed_block("③ Key Findings — 핵심 발견 3가지 (강의 session-18·31 패턴)",
                              finding_paras, C_BLUE, st, 182*mm))

    # ============ 페이지 2 ============
    story.append(PageBreak())

    story.append(Paragraph("<font color='#1565C0'>모바일 이식 액션 플랜 — 데이터 기반 권고</font>", st["title"]))
    story.append(Spacer(1, 3))

    # 모바일 시사점 + 플레이타임 차트
    chart_row3 = Table(
        [[Image("charts_v2/mobile_impl.png",     width=88*mm, height=52*mm),
          Image("charts_v2/playtime_bucket.png", width=88*mm, height=52*mm)]],
        colWidths=[90*mm, 90*mm], hAlign="CENTER"
    )
    chart_row3.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row3)
    story.append(Spacer(1, 4))

    # ============ 4. RECOMMENDATIONS ============
    recs = derive_recommendations(ins)
    rec_paras = []
    for r in recs:
        priority_color = {1: C_NEG, 2: C_POS, 3: C_MIX}.get(r["priority"], C_DARK)
        rec_paras.append(Paragraph(
            f'<font color="{priority_color.hexval()}"><b>[P{r["priority"]}]</b></font> {r["action"]}<br/>'
            f'<font color="#555">└ 사유: {r["reason"]}</font>',
            st["body"]
        ))
        rec_paras.append(Spacer(1, 2))
    story.append(boxed_block("④ Recommendations — 우선순위별 권장 조치 (강의 session-31 표준)",
                              rec_paras, C_BLUE, st, 182*mm))
    story.append(Spacer(1, 4))

    # ============ 5. EXPECTED IMPACT ============
    imp = derive_expected_impact(ins)
    imp_paras = []
    for i, t in enumerate(imp, 1):
        imp_paras.append(Paragraph(f"• {t}", st["bullet"]))
    story.append(boxed_block("⑤ Expected Impact — 기대 효과 (정량 목표)",
                              imp_paras, C_POS, st, 182*mm))
    story.append(Spacer(1, 4))

    # ============ ABSA 부정 EVIDENCE 표 ============
    evidence_paras = []
    pri = ins.get("aspect_priority", [])[:3]
    if pri:
        for p in pri:
            evs = (ins.get("aspect_evidence", {}).get(p["aspect"], {}).get("negative") or [])[:2]
            if not evs: continue
            quote = " / ".join(f'"{e}"' for e in evs)
            evidence_paras.append(Paragraph(
                f'<b>{p["aspect_kr"]}</b> ({p["neg"]}건, 부정률 {p["neg_rate"]:.0f}%) — '
                f'<font color="#666">{quote}</font>',
                st["small"]
            ))
    if evidence_paras:
        story.append(boxed_block("부정 영역 실제 인용 (ABSA evidence — 강의 session-18 패턴)",
                                  evidence_paras, C_NEG, st, 182*mm))
        story.append(Spacer(1, 4))

    # ============ LIMITATIONS + FOOTER ============
    lim = ("<b>분석 한계점</b>: "
           "(1) 한국어 리뷰만 분석 → 영어/타 언어권 의견 미반영, "
           "(2) Steam 플랫폼 한정 (콘솔 미포함), "
           "(3) 짧은 리뷰 146건은 자동 제외(분석 정확도 확보 목적), "
           "(4) LLM 분류 신뢰도 약 ±5% (강의 session-25 신뢰도 해석 기준), "
           "(5) 표본 254건은 통계적 방향성 확인용이며 정확한 비율 추론에는 1000건+ 권장.")
    story.append(Paragraph(lim, st["footer"]))
    story.append(Spacer(1, 2))
    foot = ("방법론: 강의 session-08(API 수집) → session-15(전처리) → session-22(멀티태스크 프롬프트) → "
            "session-23(다차원 통합 분석) → session-18(ABSA + 다차원 감정) → session-31(인사이트 도출·스토리텔링) "
            "전 과정을 자체 파이프라인(Python+FastAPI+SQLite+Gemini)으로 엔드투엔드 재구현.")
    story.append(Paragraph(foot, st["footer"]))

    doc.build(story)
    print("✅ PDF 생성 완료 → 팰월드_스팀리뷰_분석서_v2.pdf")


if __name__ == "__main__":
    make_report()
