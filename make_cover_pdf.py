"""표지 PDF — Light Cream Paper Theme (대시보드 톤앤매너 통일)

Layout:
  ┌─────────────────────────────┐
  │  (gradient accent line)     │
  │                             │
  │  GAME ANALYTICS (badge)     │
  │  팰월드                      │
  │  AI 리뷰데이터 분석 툴        │
  │  ─── thin rule ───          │
  │  PROTOTYPE · 2026           │
  │                             │
  │  ┌───────────────────────┐  │
  │  │  ● ● ●  window bar   │  │
  │  │   Steam Screenshot    │  │
  │  │                       │  │
  │  └───────────────────────┘  │
  │                             │
  │  ○ 149.2h   ○ 57/57  ○ 매우긍정│
  │                             │
  │  ── tech stack ──           │
  │  조경환                      │
  └─────────────────────────────┘
"""

import io
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

# ─── Paths ─────────────────────────────────────────────────────────────
COVER_IMAGE = r"C:\Users\Admin\Downloads\제목 없음.png"
EXISTING_PDF = r"C:\Users\Admin\Downloads\새 폴더 (4)\상세설명.pdf"
OUTPUT_PDF = r"C:\Users\Admin\Downloads\AI리뷰데이터분석툴_프로토타입_조경환.pdf"

# ─── Design Tokens (Light Cream Paper — 대시보드 통일) ──────────────────
BG          = HexColor("#FBF9F2")     # 메인 배경: 크림 페이퍼
CARD_BG     = HexColor("#FFFFFF")     # 카드 배경
GHOST_FILL  = HexColor("#F4F1E8")     # 강조 카드 배경
BORDER      = HexColor("#18181B17")   # 카드 보더 (zinc 9%)
BORDER_STR  = HexColor("#DDDAD1")     # 실선 보더 (인쇄용)
TEXT_DARK   = HexColor("#0B0B0F")     # 본문 텍스트
TEXT_SUB    = HexColor("#3F3F46")     # 서브 텍스트 zinc-700
TEXT_MUTE   = HexColor("#71717a")     # 흐린 텍스트 zinc-500
ACCENT      = HexColor("#0047BB")     # 웹젠 블루
BURGUNDY    = HexColor("#800020")     # 버건디
GREEN       = HexColor("#1D7044")     # 성공 그린
RED         = HexColor("#B12525")     # 에러 레드
AMBER       = HexColor("#A56B16")     # 앰버

# ─── Fonts ─────────────────────────────────────────────────────────────
FONTS_DIR = r"C:\Users\Admin\AppData\Local\Microsoft\Windows\Fonts"

def _reg(file, name):
    pdfmetrics.registerFont(TTFont(name, f"{FONTS_DIR}\\{file}"))
    return name

F_BLACK    = _reg("Pretendard-Black.ttf",     "PBlack")
F_EXTRABOLD= _reg("Pretendard-ExtraBold.ttf", "PExtraBold")
F_BOLD     = _reg("Pretendard-Bold.ttf",      "PBold")
F_SEMI     = _reg("Pretendard-SemiBold.ttf",  "PSemi")
F_MEDIUM   = _reg("Pretendard-Medium.ttf",    "PMed")
F_REGULAR  = _reg("Pretendard-Regular.ttf",   "PReg")
F_LIGHT    = _reg("Pretendard-Light.ttf",     "PLight")


def rr(c, x, y, w, h, r, fill=None, stroke=None, lw=0.5):
    """Rounded rect helper."""
    c.saveState()
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=bool(fill), stroke=bool(stroke))
    c.restoreState()


def create_cover():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4  # 595.27 x 841.89 pt

    # ── Background (크림 페이퍼) ──
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top accent line (gradient: blue → burgundy) ──
    # reportlab은 단일 gradient를 직접 지원하지 않으므로 두 색상 구간으로 구분
    half = W / 2
    c.setLineWidth(4)
    c.setStrokeColor(ACCENT)
    c.line(0, H - 2, half, H - 2)
    c.setStrokeColor(BURGUNDY)
    c.line(half, H - 2, W, H - 2)

    # ── Bottom accent line ──
    c.setStrokeColor(BORDER_STR)
    c.setLineWidth(2)
    c.line(0, 1, W, 1)

    # ── Header area ──
    cx = W / 2
    top = H - 32 * mm

    # Category badge
    tag_text = "GAME ANALYTICS"
    c.setFont(F_BOLD, 8.5)
    c.setFillColor(ACCENT)
    tw = c.stringWidth(tag_text, F_BOLD, 8.5)
    tag_w = tw + 20
    tag_h = 20
    tag_x = cx - tag_w / 2
    tag_y = top
    # Badge background
    rr(c, tag_x, tag_y, tag_w, tag_h, 10,
       fill=Color(0, 0.28, 0.73, alpha=0.06),
       stroke=Color(0, 0.28, 0.73, alpha=0.2), lw=0.6)
    c.drawCentredString(cx, tag_y + 6, tag_text)

    # Main title
    title_y = top - 22
    c.setFont(F_BLACK, 32)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(cx, title_y, "팰월드")

    c.setFont(F_EXTRABOLD, 22)
    c.setFillColor(TEXT_SUB)
    c.drawCentredString(cx, title_y - 32, "AI 리뷰데이터 분석 툴")

    # Thin horizontal rule
    rule_y = title_y - 52
    rule_w = 25
    c.setStrokeColor(BORDER_STR)
    c.setLineWidth(0.5)
    c.line(cx - rule_w, rule_y, cx + rule_w, rule_y)

    # Subtitle
    c.setFont(F_SEMI, 10)
    c.setFillColor(TEXT_MUTE)
    c.drawCentredString(cx, rule_y - 16, "PROTOTYPE  ·  2026")

    # ── Screenshot image ──
    img_margin_x = 18 * mm
    img_top_y = rule_y - 30

    img = PILImage.open(COVER_IMAGE)
    iw, ih = img.size
    target_w = W - 2 * img_margin_x
    scale = target_w / iw
    target_h = ih * scale

    # Cap max height
    max_h = H * 0.46
    if target_h > max_h:
        target_h = max_h
        scale = target_h / ih
        target_w = iw * scale

    img_x = (W - target_w) / 2
    img_y = img_top_y - target_h

    # Image card container (white card with border)
    card_pad = 1
    rr(c, img_x - card_pad, img_y - card_pad,
       target_w + card_pad * 2, target_h + card_pad * 2 + 20,
       8, fill=CARD_BG, stroke=BORDER_STR, lw=0.6)

    # Window bar
    bar_h = 18
    bar_y = img_y + target_h + card_pad
    c.saveState()
    c.setFillColor(GHOST_FILL)
    c.rect(img_x - card_pad + 0.5, bar_y, target_w + card_pad * 2 - 1, bar_h, fill=1, stroke=0)
    # Window dots
    dot_r = 3.5
    dot_y_center = bar_y + bar_h / 2
    dot_start_x = img_x + 8
    for i, color in enumerate([RED, AMBER, GREEN]):
        c.setFillColor(color)
        c.circle(dot_start_x + i * 12, dot_y_center, dot_r, fill=1, stroke=0)
    # Bar bottom border
    c.setStrokeColor(BORDER_STR)
    c.setLineWidth(0.3)
    c.line(img_x - card_pad, bar_y, img_x + target_w + card_pad, bar_y)
    c.restoreState()

    # Draw image
    c.drawImage(COVER_IMAGE, img_x, img_y, width=target_w, height=target_h,
                preserveAspectRatio=True, anchor='nw', mask='auto')

    # ── Stat pills below image ──
    pill_y = img_y - 14 * mm
    pill_h = 11 * mm
    pill_gap = 5 * mm
    pill_data = [
        ("플레이 시간", "149.2시간", ACCENT),
        ("도전 과제 달성", "57 / 57  (100%)", GREEN),
        ("Steam 종합 평가", "매우 긍정적", GREEN),
    ]
    total_pill_w = W - 2 * 18 * mm
    pill_w = (total_pill_w - 2 * pill_gap) / 3

    for i, (label, value, color) in enumerate(pill_data):
        px = 18 * mm + i * (pill_w + pill_gap)
        py = pill_y

        # Pill background (white card)
        rr(c, px, py, pill_w, pill_h, 6, fill=CARD_BG, stroke=BORDER_STR, lw=0.5)

        # Colored left accent bar
        c.saveState()
        c.setFillColor(color)
        c.rect(px + 1.5, py + 2, 2.5, pill_h - 4, fill=1, stroke=0)
        c.restoreState()

        # Label
        c.setFont(F_BOLD, 7)
        c.setFillColor(TEXT_MUTE)
        c.drawString(px + 10, py + pill_h - 10, label)

        # Value
        c.setFont(F_EXTRABOLD, 13)
        c.setFillColor(color)
        c.drawString(px + 10, py + 4, value)

    # ── Footer ──
    c.setFont(F_MEDIUM, 8)
    c.setFillColor(TEXT_MUTE)
    c.drawCentredString(cx, 16 * mm,
        "Steam Storefront API  ·  FastAPI  ·  SQLite  ·  Gemini 2.0 Flash  ·  Chart.js")

    c.setFont(F_BOLD, 9)
    c.setFillColor(TEXT_SUB)
    c.drawCentredString(cx, 10 * mm, "조경환")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def main():
    print("Creating cream paper cover...")
    cover_buf = create_cover()
    cover_r = PdfReader(cover_buf)
    existing_r = PdfReader(EXISTING_PDF)
    writer = PdfWriter()

    for p in cover_r.pages:
        writer.add_page(p)
    for p in existing_r.pages:
        writer.add_page(p)

    with open(OUTPUT_PDF, "wb") as f:
        writer.write(f)
    print(f"Done! {len(writer.pages)} pages -> {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
