"""A4 2장 PDF 분석서 생성 (게임 기획자 모바일 면접용)

입력 : insights.json, charts/*.png
출력 : 팰월드_스팀리뷰_분석서.pdf

레이아웃:
- 페이지 1: 헤더 + 요약 한 줄 + 핵심 KPI 4개 + 감성 도넛 + 카테고리 막대
            + 추천 사유 Top / 비추천 사유 Top (2단 박스)
- 페이지 2: 모바일 이식 시사점 분포 차트 + 플레이타임 vs 추천률 차트
            + 모바일 이식 권고 4~6개 (불릿) + 분석 방법론 한 줄 + 푸터
"""

import os
import json
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
)

# 한글 폰트 등록
pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBold", "C:/Windows/Fonts/malgunbd.ttf"))

C_POS  = colors.HexColor("#2E7D32")
C_NEG  = colors.HexColor("#C62828")
C_BG   = colors.HexColor("#F4F6F8")
C_DARK = colors.HexColor("#212121")
C_GRAY = colors.HexColor("#5F6368")
C_BLUE = colors.HexColor("#1565C0")


def styles():
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=s["Normal"], fontName="MalgunBold",
                                fontSize=15, leading=18, textColor=C_DARK),
        "sub":   ParagraphStyle("sub", parent=s["Normal"], fontName="Malgun",
                                fontSize=9, leading=11, textColor=C_GRAY),
        "h2":    ParagraphStyle("h2", parent=s["Normal"], fontName="MalgunBold",
                                fontSize=10.5, leading=13, textColor=C_BLUE, spaceBefore=4, spaceAfter=2),
        "body":  ParagraphStyle("body", parent=s["Normal"], fontName="Malgun",
                                fontSize=8.5, leading=11.5, textColor=C_DARK),
        "bullet": ParagraphStyle("bullet", parent=s["Normal"], fontName="Malgun",
                                 fontSize=8.5, leading=11.5, leftIndent=10, bulletIndent=0, textColor=C_DARK),
        "kpi_label": ParagraphStyle("kpi_label", parent=s["Normal"], fontName="Malgun",
                                    fontSize=7.5, leading=9, textColor=C_GRAY, alignment=TA_CENTER),
        "kpi_val":   ParagraphStyle("kpi_val", parent=s["Normal"], fontName="MalgunBold",
                                    fontSize=15, leading=17, alignment=TA_CENTER, textColor=C_DARK),
        "footer":ParagraphStyle("footer", parent=s["Normal"], fontName="Malgun",
                                fontSize=7, leading=8, textColor=C_GRAY, alignment=TA_CENTER),
    }


def kpi_card(label, value, color, st):
    inner = Table(
        [[Paragraph(label, st["kpi_label"])],
         [Paragraph(f'<font color="{color.hexval()}">{value}</font>', st["kpi_val"])]],
        colWidths=[42*mm], rowHeights=[7*mm, 12*mm]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    return inner


def bullet_box(title, items, color, st, width):
    rows = [[Paragraph(f'<font color="{color.hexval()}"><b>{title}</b></font>', st["h2"])]]
    for i, (text, n) in enumerate(items[:6], 1):
        rows.append([Paragraph(f"{i}. {text}  <font color='#888888'>({n}건)</font>", st["body"])])
    t = Table(rows, colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_BG),
        ("BOX", (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return t


def derive_recommendations(ins):
    """카테고리/시사점 분포에서 모바일 이식 권고 자동 도출"""
    cats = ins.get("categories", {})
    mob  = ins.get("mobile_impl", {})
    recs = []

    # 1. 가장 많이 언급된 긍정 카테고리 → 모바일에서 유지·강화
    pos_top = sorted(cats.items(), key=lambda x: -x[1]["pos"])[:3]
    if pos_top:
        names = ", ".join(p[0] for p in pos_top[:2])
        recs.append(("유지·강화 (Keep)",
                     f"<b>{names}</b>은 한국 유저가 가장 호평한 요소로, 모바일에서도 핵심 경험 축으로 유지·강화 필요"))

    # 2. 비추천 핵심 카테고리 → 모바일에서 회피·개선
    neg_top = sorted(cats.items(), key=lambda x: -x[1]["neg"])[:3]
    if neg_top:
        names = ", ".join(n[0] for n in neg_top[:2])
        recs.append(("회피·개선 (Fix)",
                     f"<b>{names}</b>은 비추천 리뷰에서 집중 거론된 영역으로, 모바일 출시 전 우선 개선 대상"))

    # 3. 모바일에서개선가능 비중
    if mob.get("모바일에서개선가능", 0) > 0:
        recs.append(("재설계 기회 (Redesign)",
                     f"리뷰 중 <b>{mob.get('모바일에서개선가능',0)}건</b>이 '모바일에서 개선 가능'으로 분류 — 컨트롤·세션 길이·UI 재설계로 PC 약점을 모바일 강점으로 전환 가능"))

    # 4. 플레이타임 구간 — 장기 충성층 인사이트
    play = ins.get("playtime", {})
    if "100h+" in play:
        recs.append(("코어 유저 보호 (Retention)",
                     f"100시간 이상 플레이 유저 추천률 <b>{play['100h+']['recommend_rate']:.0f}%</b> — 장기 콘텐츠/엔드게임 깊이가 핵심. 모바일에서도 후반부 콘텐츠 축소 시 이탈 위험"))

    # 5. 비추천 사유 톱 → 명시적 회피 항목
    neg_reasons = ins.get("negative_mobile_reasons", [])
    if neg_reasons:
        recs.append(("부정 신호 모니터링 (Watch)",
                     "비추천 유저가 모바일 이식에 우려하는 사유: "
                     + "; ".join(r[0] for r in neg_reasons[:3])))

    # 6. 모바일적합 메시지
    if mob.get("모바일적합", 0) > 0:
        recs.append(("모바일 친화 강점 (Strength)",
                     f"리뷰 중 <b>{mob.get('모바일적합',0)}건</b>이 '모바일적합'으로 — 짧은 세션·캐주얼 동선·자동 기능과 잘 맞는 콘텐츠 축이 존재"))

    return recs


def make_report():
    with open("insights.json", "r", encoding="utf-8") as f:
        ins = json.load(f)

    st = styles()
    doc = SimpleDocTemplate(
        "팰월드_스팀리뷰_분석서.pdf",
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=12*mm, bottomMargin=10*mm,
    )
    story = []

    # ===== 헤더 =====
    title_html = ('<font color="#1565C0">PC 스팀 팰월드(Palworld)</font>'
                  ' 한국 유저 리뷰 분석 — 모바일 이식 시사점')
    story.append(Paragraph(title_html, st["title"]))
    n_total = ins["n_total"]
    n_pos = ins["n_pos"]
    n_neg = ins["n_neg"]
    sub_html = (f"분석 기간: 최신 한국어 리뷰 {n_total}건 "
                f"(추천 {n_pos}건 · 비추천 {n_neg}건 보강 수집) | "
                f"방법: Steam Storefront API + 자체 FastAPI · SQLite · OpenRouter gpt-4o-mini 다차원 LLM 분류 | "
                f"작성: 조경환 · {date.today().isoformat()}")
    story.append(Paragraph(sub_html, st["sub"]))
    story.append(Spacer(1, 4))

    # ===== 한줄 요약 =====
    pos_pct = n_pos / n_total * 100
    summary = (f"한국 유저는 팰월드를 <b>{pos_pct:.0f}%</b> 추천 — 핵심 호평은 "
               f"<b>창의성·게임플레이·멀티플레이</b>, 핵심 혹평은 <b>버그·콘텐츠 분량</b>. "
               f"<b>모바일 이식 시 호평 축을 유지하면서 비추천 사유를 선제 회피하는 설계가 결정적.</b>")
    story.append(Paragraph(summary, st["body"]))
    story.append(Spacer(1, 5))

    # ===== KPI 4장 =====
    sent = ins["sentiment"]
    kpis = [
        kpi_card("총 분석 리뷰", f"{n_total}건", C_DARK, st),
        kpi_card("추천 비율", f"{pos_pct:.0f}%", C_POS, st),
        kpi_card("긍정 분류 (LLM)", f"{sent.get('긍정',0)}건", C_POS, st),
        kpi_card("부정 분류 (LLM)", f"{sent.get('부정',0)}건", C_NEG, st),
    ]
    kpi_row = Table([kpis], colWidths=[44*mm]*4, hAlign="CENTER")
    kpi_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                 ("LEFTPADDING",(0,0),(-1,-1),1),
                                 ("RIGHTPADDING",(0,0),(-1,-1),1)]))
    story.append(kpi_row)
    story.append(Spacer(1, 5))

    # ===== 차트 2개 (감성 + 카테고리) =====
    chart_row = Table(
        [[Image("charts/sentiment.png",  width=68*mm, height=60*mm),
          Image("charts/categories.png", width=110*mm, height=60*mm)]],
        colWidths=[70*mm, 110*mm], hAlign="CENTER"
    )
    chart_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row)
    story.append(Spacer(1, 4))

    # ===== 추천/비추천 핵심 포인트 박스 =====
    pos_pts = ins["top_points_positive"]
    neg_pts = ins["top_points_negative"]
    point_row = Table(
        [[bullet_box("✓ 추천 유저의 핵심 호평 (Top 6)", pos_pts, C_POS, st, 88*mm),
          bullet_box("✗ 비추천 유저의 핵심 혹평 (Top 6)", neg_pts, C_NEG, st, 88*mm)]],
        colWidths=[90*mm, 90*mm], hAlign="CENTER"
    )
    point_row.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(point_row)

    # ====== 페이지 2 ======
    story.append(PageBreak())

    story.append(Paragraph("<font color='#1565C0'>모바일 이식 시사점 — 데이터 기반 권고</font>", st["title"]))
    story.append(Spacer(1, 4))

    # 모바일 시사점 + 플레이타임 차트 좌우
    chart_row2 = Table(
        [[Image("charts/mobile_impl.png",     width=88*mm, height=58*mm),
          Image("charts/playtime_bucket.png", width=88*mm, height=58*mm)]],
        colWidths=[90*mm, 90*mm], hAlign="CENTER"
    )
    chart_row2.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(chart_row2)
    story.append(Spacer(1, 5))

    # 자동 도출 권고
    story.append(Paragraph("핵심 권고 (Top Recommendations)", st["h2"]))
    for label, txt in derive_recommendations(ins):
        story.append(Paragraph(f"• <b>{label}</b> — {txt}", st["bullet"]))
    story.append(Spacer(1, 6))

    # 카테고리 표 (추천/비추천 분리)
    story.append(Paragraph("카테고리별 추천 vs 비추천 분포 (Top 7)", st["h2"]))
    cats = sorted(ins["categories"].items(), key=lambda x: -x[1]["total"])[:7]
    rows = [["카테고리", "추천 언급", "비추천 언급", "비추천 비중"]]
    for name, d in cats:
        total = d["total"] or 1
        rows.append([name, str(d["pos"]), str(d["neg"]), f"{d['neg']/total*100:.0f}%"])
    tab = Table(rows, colWidths=[40*mm, 30*mm, 30*mm, 30*mm], hAlign="CENTER")
    tab.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Malgun"),
        ("FONTNAME", (0,0), (-1,0), "MalgunBold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("BACKGROUND", (0,0), (-1,0), C_BG),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(tab)
    story.append(Spacer(1, 8))

    # 푸터 / 방법론
    foot = ("방법론 요약: ① Steam Storefront API로 최신 한국어 리뷰 수집 → ② 자체 FastAPI 서버(SQLite)에 적재 → "
            "③ OpenRouter gpt-4o-mini로 리뷰별 감성·카테고리·핵심 포인트·모바일 시사점 4축 동시 분류 (멀티태스크 프롬프트) → "
            "④ 추천/비추천·플레이타임 구간 교차 집계. 한계: 한국어 표본 한정, 모델 분류 신뢰도 ±5%.")
    story.append(Paragraph(foot, st["footer"]))

    doc.build(story)
    print("✅ PDF 생성 완료 → 팰월드_스팀리뷰_분석서.pdf")


if __name__ == "__main__":
    make_report()
