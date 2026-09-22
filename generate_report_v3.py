"""v3 A4 3장 PDF — 강의 5부 구조 + 표본 설계 박스 + 시계열 + 가독성 강화."""

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
from config import cfg

CHARTS_V3_DIR = os.path.join(cfg.project_dir(), "charts_v3")

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
                                fontSize=16, leading=19, textColor=C_DARK),
        "sub":   ParagraphStyle("sub", parent=s["Normal"], fontName="Malgun",
                                fontSize=9, leading=11.5, textColor=C_GRAY),
        "h2":    ParagraphStyle("h2", parent=s["Normal"], fontName="MalgunBold",
                                fontSize=12, leading=15, textColor=C_BLUE, spaceBefore=3, spaceAfter=3),
        "body":  ParagraphStyle("body", parent=s["Normal"], fontName="Malgun",
                                fontSize=9.5, leading=13, textColor=C_DARK),
        "small": ParagraphStyle("small", parent=s["Normal"], fontName="Malgun",
                                fontSize=8.5, leading=11, textColor=C_DARK),
        "bullet":ParagraphStyle("bullet", parent=s["Normal"], fontName="Malgun",
                                fontSize=9.5, leading=13, leftIndent=10, textColor=C_DARK),
        "kpi_label": ParagraphStyle("kpi_label", parent=s["Normal"], fontName="Malgun",
                                    fontSize=8.5, leading=10, textColor=C_GRAY, alignment=TA_CENTER),
        "kpi_val":   ParagraphStyle("kpi_val", parent=s["Normal"], fontName="MalgunBold",
                                    fontSize=18, leading=21, alignment=TA_CENTER, textColor=C_DARK),
        "exec":  ParagraphStyle("exec", parent=s["Normal"], fontName="Malgun",
                                fontSize=10.5, leading=15, textColor=C_DARK, leftIndent=6),
        "footer":ParagraphStyle("footer", parent=s["Normal"], fontName="Malgun",
                                fontSize=7.5, leading=9.5, textColor=C_GRAY, alignment=TA_LEFT),
    }


def kpi_card(label, value, color, st, w=44*mm):
    inner = Table(
        [[Paragraph(label, st["kpi_label"])],
         [Paragraph(f'<font color="{color.hexval()}">{value}</font>', st["kpi_val"])]],
        colWidths=[w], rowHeights=[7*mm, 13*mm]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, C_LINE),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    return inner


def boxed_block(title, body_items, color, st, width):
    rows = [[Paragraph(f'<font color="{color.hexval()}"><b>{title}</b></font>', st["h2"])]]
    for it in body_items:
        rows.append([it])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, C_LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    return t


# 인사이트 도출 로직 (v2와 동일 — 강의 session-31 패턴)
def derive_key_findings(ins):
    findings = []
    pri = ins.get("aspect_priority", [])
    if pri:
        w = pri[0]
        findings.append({
            "type": "최우선 개선 영역 (모바일 1순위 회피)",
            "finding": f"6-Aspect 중 <b>{w['aspect_kr']}</b>의 부정 비율 <b>{w['neg_rate']:.0f}%</b> (언급 {w['mentioned']}회 · 부정 {w['neg']}건)",
            "impact": "한국 유저 비추천의 1순위 사유. 모바일에서 동일 문제 시 출시 직후 부정 리뷰 폭주 위험. <b>QA 예산 1.5~2배 책정 권고</b>",
        })
    emo = ins.get("emotion", {})
    d = emo.get("DISAPPOINTMENT", 0); a = emo.get("ANGER", 0); b = emo.get("BOREDOM", 0)
    if d+a+b > 0:
        if a >= max(d,b):
            tag, n, impact = "ANGER(분노)", a, "환불·악평 위험. <b>모바일 출시 시 CS 응대 시나리오 사전 준비 + 핫픽스 라인 필수</b>"
        elif d >= b:
            tag, n, impact = "DISAPPOINTMENT(실망)", d, "기대치 대비 미달 — 콘텐츠/완성도 보강만으로 회복 가능. 분노보다 다루기 쉬움"
        else:
            tag, n, impact = "BOREDOM(지루함)", b, "엔드게임/콘텐츠 깊이 부족 — 모바일에서 짧은 세션이라도 진행감 끊임없이 제공해야 이탈 방지"
        findings.append({
            "type": "비추천 유저의 주된 감정 (강의 session-18 다차원)",
            "finding": f"가장 빈도 높은 부정 감정: <b>{tag} {n}건</b>",
            "impact": impact,
        })
    play = ins.get("playtime", {})
    if play:
        worst = min(play.items(), key=lambda x: x[1]["recommend_rate"])
        core = play.get("100h+", {})
        if worst and core:
            findings.append({
                "type": "이탈 위험 구간 (온보딩 핵심 변수)",
                "finding": f"플레이타임 <b>{worst[0]}</b> 구간 추천률 <b>{worst[1]['recommend_rate']:.0f}%</b> (최저, n={worst[1]['n']}). 100시간 이상 코어층은 <b>{core.get('recommend_rate', 0):.0f}%</b>",
                "impact": f"모바일은 짧은 세션이 본질 — {worst[0]} 구간을 못 넘기면 PC보다 빠르게 이탈. <b>1주차 온보딩 설계가 성공 변수</b>",
            })
    return findings[:3]


def derive_recommendations(ins):
    recs = []
    pri = ins.get("aspect_priority", [])
    mob = ins.get("mobile_impl", {})
    aspects = ins.get("aspects", {})
    if pri:
        w = pri[0]
        evs = (ins.get("aspect_evidence", {}).get(w["aspect"], {}).get("negative") or [])
        ev_text = f' 근거 인용: <font color="#777">"{evs[0][:50]}"</font>' if evs else ""
        recs.append({"priority":1,
            "action": f"<b>{w['aspect_kr']} 안정성 확보</b> — 모바일 출시 전 QA 예산 1.5~2배 책정",
            "reason": f"PC 한국 유저 비추천 1순위(부정률 {w['neg_rate']:.0f}%). 모바일은 디바이스 다양성으로 더 악화 가능.{ev_text}"})
    best_a, best_pos = None, 0
    for a, s in aspects.items():
        if s["POSITIVE"] > best_pos:
            best_pos = s["POSITIVE"]; best_a = a
    if best_a:
        kr_map = {"graphics":"그래픽","gameplay":"게임플레이","story":"스토리",
                  "performance":"성능·버그","value":"가격·가성비","multiplayer":"멀티플레이"}
        evs = (ins.get("aspect_evidence", {}).get(best_a, {}).get("positive") or [])
        ev_text = f' 근거 인용: <font color="#777">"{evs[0][:50]}"</font>' if evs else ""
        recs.append({"priority":2,
            "action": f"<b>{kr_map.get(best_a, best_a)} 강점을 모바일에서도 핵심 경험 축으로 유지</b>",
            "reason": f"한국 유저 호평 최다 영역(POSITIVE {best_pos}건). 모바일에서 축소 시 IP 정체성 손실.{ev_text}"})
    redesign = mob.get("NEEDS_REDESIGN", 0); fit = mob.get("FIT", 0); unfit = mob.get("UNFIT", 0)
    total = fit + redesign + unfit
    if total > 0:
        ratio = (fit+redesign)/total*100
        recs.append({"priority":3,
            "action": f"<b>'재설계 시 적합' {redesign}건 영역을 모바일 네이티브로 재구성</b>",
            "reason": f"모바일 적합도 응답 {total}건 중 {ratio:.0f}%가 '적합/재설계 시 적합'. 단순 포팅이 아닌 폼팩터 재설계로 시장 확장 가능."})
    return recs[:3]


def derive_expected_impact(ins):
    pri = ins.get("aspect_priority", [])
    fit = ins.get("mobile_impl", {}).get("FIT", 0)
    red = ins.get("mobile_impl", {}).get("NEEDS_REDESIGN", 0)
    targets = []
    if pri:
        w = pri[0]
        tr = max(15, int(w["neg_rate"]) - 30)
        targets.append(f"<b>{w['aspect_kr']}</b> 부정 비율을 {w['neg_rate']:.0f}% → <b>{tr}%대</b>로 감축")
    if fit+red > 0:
        targets.append(f"모바일 친화 영역({fit+red}건) 우선 구현으로 출시 후 8주차 D30 유지율 <b>업계 평균 +5~10%p</b> 달성")
    targets.append("출시 30일 내 한국 유저 추천률 <b>70%+</b> (PC 기준선)")
    return targets


def make_report():
    with open(cfg.project_file("insights_v3.json"),"r",encoding="utf-8") as f:
        ins = json.load(f)
    # 표본 설계 로드 (이미 생성된 거 활용)
    sd = {}
    sample_path = cfg.project_file("sample_design.json")
    if os.path.exists(sample_path):
        with open(sample_path,"r",encoding="utf-8") as f:
            sd = json.load(f)

    st = styles()
    doc = SimpleDocTemplate(
        cfg.project_file("팰월드_스팀리뷰_분석서_v3.pdf"),
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=13*mm, bottomMargin=11*mm,
    )
    story = []

    n = ins["n_total"]; n_pos = ins["n_pos"]; n_neg = ins["n_neg"]
    pos_pct = n_pos/n*100 if n else 0

    # ===== 헤더 =====
    title_html = ('<font color="#1565C0">PC 스팀 팰월드(Palworld)</font>'
                  ' 한국 유저 리뷰 분석 — 모바일 이식 시사점')
    story.append(Paragraph(title_html, st["title"]))
    sub_html = (f"분석 대상: 한국어 리뷰 <b>{n}건</b> (추천 {n_pos} · 비추천 {n_neg}, 모집단 비례 + 비추천 표본 보강) "
                f"| 방법: Steam Storefront API → 자체 FastAPI+SQLite → "
                f"Google Gemini 2.0 Flash 다차원 LLM 분석(ABSA 6-Aspect·감정·키워드 토픽·모바일 시사점) "
                f"| 작성: 조경환 · {date.today().isoformat()}")
    story.append(Paragraph(sub_html, st["sub"]))
    story.append(Spacer(1, 5))

    # ===== Executive Summary =====
    pri = ins.get("aspect_priority", [])
    worst_kr = pri[0]["aspect_kr"] if pri else ""
    worst_rate = pri[0]["neg_rate"] if pri else 0
    aspects = ins.get("aspects", {})
    best_kr = "게임플레이"; best_pos = 0
    for a, s in aspects.items():
        if s["POSITIVE"] > best_pos:
            best_pos = s["POSITIVE"]
            kr_map = {"graphics":"그래픽","gameplay":"게임플레이","story":"스토리",
                      "performance":"성능·버그","value":"가격·가성비","multiplayer":"멀티플레이"}
            best_kr = kr_map.get(a, a)
    exec_html = (f"한국 유저 추천률 <b>{pos_pct:.0f}%</b>. 핵심 호평은 <b>{best_kr}</b>({best_pos}건), "
                 f"핵심 혹평은 <b>{worst_kr}</b>(부정률 {worst_rate:.0f}%). "
                 f"<b>모바일 이식 성공의 결정 변수는 호평 축 유지 + {worst_kr} 안정성 확보 + 초기 이탈 구간 온보딩 재설계.</b>")
    story.append(boxed_block("① Executive Summary", [Paragraph(exec_html, st["exec"])], C_BLUE, st, 180*mm))
    story.append(Spacer(1, 6))

    # ===== KPI 카드 =====
    sent = ins["sentiment"]
    kpis = [
        kpi_card("총 분석 리뷰", f"{n}건", C_DARK, st),
        kpi_card("추천 비율", f"{pos_pct:.0f}%", C_POS, st),
        kpi_card("긍정 (LLM)", f"{sent.get('POSITIVE',0)}건", C_POS, st),
        kpi_card("부정 (LLM)", f"{sent.get('NEGATIVE',0)}건", C_NEG, st),
    ]
    kpi_row = Table([kpis], colWidths=[45*mm]*4, hAlign="CENTER")
    kpi_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(kpi_row)
    story.append(Spacer(1, 6))

    # ===== Current State 차트 (감성 + ABSA) =====
    story.append(Paragraph("② Current State — 현황 데이터", st["h2"]))
    chart_row = Table(
        [[Image(os.path.join(CHARTS_V3_DIR, "sentiment.png"), width=78*mm, height=64*mm),
          Image(os.path.join(CHARTS_V3_DIR, "aspects.png"),   width=104*mm, height=64*mm)]],
        colWidths=[80*mm, 104*mm], hAlign="CENTER"
    )
    chart_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row)

    # 페이지 1 끝
    story.append(PageBreak())

    # ===== 페이지 2: 감정 + 토픽 + Key Findings =====
    story.append(Paragraph("<font color='#1565C0'>심화 분석: 감정 차원 + 토픽 + 발견사항</font>", st["title"]))
    story.append(Spacer(1, 4))

    chart_row2 = Table(
        [[Image(os.path.join(CHARTS_V3_DIR, "emotion.png"), width=96*mm, height=46*mm),
          Image(os.path.join(CHARTS_V3_DIR, "topics.png"),  width=86*mm, height=46*mm)]],
        colWidths=[98*mm, 86*mm], hAlign="CENTER"
    )
    chart_row2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row2)
    story.append(Spacer(1, 5))

    # Key Findings
    finds = derive_key_findings(ins)
    finding_paras = []
    for i, f in enumerate(finds, 1):
        finding_paras.append(Paragraph(
            f'<b>{i}. {f["type"]}</b><br/>'
            f'• 발견: {f["finding"]}<br/>'
            f'• 의미: <font color="#444">{f["impact"]}</font>',
            st["body"]
        ))
        finding_paras.append(Spacer(1, 3))
    story.append(boxed_block("③ Key Findings — 핵심 발견 3가지 (강의 session-18·31 패턴)",
                             finding_paras, C_BLUE, st, 180*mm))

    # 페이지 2 끝
    story.append(PageBreak())

    # ===== 페이지 3: 모바일 + 플레이타임 + 시계열 + Recommendations + Sample Design =====
    story.append(Paragraph("<font color='#1565C0'>모바일 이식 액션 플랜 + 표본 설계</font>", st["title"]))
    story.append(Spacer(1, 4))

    chart_row3 = Table(
        [[Image(os.path.join(CHARTS_V3_DIR, "mobile_impl.png"), width=88*mm, height=44*mm),
          Image(os.path.join(CHARTS_V3_DIR, "playtime.png"),    width=88*mm, height=44*mm)]],
        colWidths=[90*mm, 90*mm], hAlign="CENTER"
    )
    chart_row3.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row3)
    story.append(Spacer(1, 4))

    # 시계열 (있을 때만)
    timeline_path = os.path.join(CHARTS_V3_DIR, "timeline.png")
    if os.path.exists(timeline_path):
        story.append(Image(timeline_path, width=180*mm, height=44*mm))
        story.append(Spacer(1, 4))

    # Recommendations
    recs = derive_recommendations(ins)
    rec_paras = []
    for r in recs:
        col = {1: C_NEG, 2: C_POS, 3: C_MIX}.get(r["priority"], C_DARK)
        rec_paras.append(Paragraph(
            f'<font color="{col.hexval()}"><b>[P{r["priority"]}]</b></font> {r["action"]}<br/>'
            f'<font color="#555">└ 사유: {r["reason"]}</font>',
            st["body"]
        ))
        rec_paras.append(Spacer(1, 2))
    story.append(boxed_block("④ Recommendations — P1·P2·P3 (강의 session-31 표준)",
                             rec_paras, C_BLUE, st, 180*mm))
    story.append(Spacer(1, 5))

    # Expected Impact
    imp = derive_expected_impact(ins)
    imp_paras = [Paragraph(f"• {t}", st["bullet"]) for t in imp]
    story.append(boxed_block("⑤ Expected Impact — 기대 효과 (정량 목표)",
                             imp_paras, C_POS, st, 180*mm))
    story.append(Spacer(1, 5))

    # Sample Design 박스 (강의 session-12·25)
    if sd:
        pop = sd.get("population", {})
        cs = sd.get("current_sample", {})
        rs = sd.get("required_sample_sizes", {})
        sd_paras = [
            Paragraph(
                f"• <b>모집단</b>: 한국어 리뷰 <b>{pop.get('total',0):,}건</b> "
                f"(추천 {pop.get('positive',0):,} · 비추천 {pop.get('negative',0):,}, "
                f"비추천 비율 {pop.get('neg_rate',0)*100:.1f}%). Steam 평가: <b>{pop.get('score','')}</b>",
                st["body"]
            ),
            Paragraph(
                f"• <b>95% 신뢰수준 표본 크기</b> (Cochran + 유한모집단 보정, p=0.5, z=1.96): "
                f"±5%p → {rs.get('e_5pct','?')}건 · ±3%p → {rs.get('e_3pct','?')}건",
                st["body"]
            ),
            Paragraph(
                f"• <b>본 분석 표본</b>: 수집 {cs.get('collected','?')}건 / 분석 {n}건 "
                f"→ 도달 오차한계 <b>±{cs.get('margin_of_error_analyzed_pct','?')}%p @ 95% CI</b>",
                st["body"]
            ),
            Paragraph(
                f"• <b>표집 전략</b>: 비추천을 모집단 비율 {pop.get('neg_rate',0)*100:.1f}%에서 "
                f"의도적으로 ~28%까지 over-sampling — 소수 집단의 부정 인사이트 깊이 확보 (강의 session-12)",
                st["body"]
            ),
        ]
        story.append(boxed_block("⑥ Sample Design — 표본 설계 (강의 session-12·25)",
                                 sd_paras, C_DARK, st, 180*mm))
        story.append(Spacer(1, 5))

    # Limitations + Footer
    lim = ("<b>분석 한계점</b>: "
           "(1) 한국어 한정 → 영어/타 언어권 의견 미반영, "
           "(2) Steam 플랫폼 한정 (콘솔 미포함), "
           "(3) 짧은 리뷰 자동 제외 → 짧은 의견은 표본에서 배제, "
           "(4) LLM 분류 신뢰도 ±5% 수준 (강의 session-25 신뢰도 해석 기준), "
           "(5) 분석 표본의 비추천 비율은 모집단 대비 의도적 over-sampling — 전체 추정 시 가중치 보정 권장.")
    story.append(Paragraph(lim, st["footer"]))
    story.append(Spacer(1, 2))
    foot = ("방법론: 강의 session-08(API 수집) → 12(샘플링) → 14·17(프롬프트) → 22(멀티태스크) → "
            "23(다차원 통합) → 18(ABSA + 다차원 감정) → 25(신뢰도) → 27(시계열) → 31(인사이트 도출). "
            "자체 파이프라인(Python+FastAPI+SQLite+Gemini)으로 엔드투엔드 재구현.")
    story.append(Paragraph(foot, st["footer"]))

    doc.build(story)
    print("✅ PDF v3 생성 → 팰월드_스팀리뷰_분석서_v3.pdf")


if __name__ == "__main__":
    make_report()
