import io
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ─── Paths ─────────────────────────────────────────────────────────────
COVER_IMAGE = r"C:\Users\Admin\.gemini\antigravity\brain\9deba450-15a6-4014-af9f-252bb03733e6\dashboard_screenshot_1780498607400.png"
OUTPUT_PDF = r"c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\P의거짓_포트폴리오.pdf"

# ─── Design Tokens ──────────────────
BG          = HexColor("#FBF9F2")
CARD_BG     = HexColor("#FFFFFF")
GHOST_FILL  = HexColor("#F4F1E8")
BORDER_STR  = HexColor("#DDDAD1")
TEXT_DARK   = HexColor("#0B0B0F")
TEXT_SUB    = HexColor("#3F3F46")
TEXT_MUTE   = HexColor("#71717a")
ACCENT      = HexColor("#0047BB")
BURGUNDY    = HexColor("#800020")
GREEN       = HexColor("#1D7044")
RED         = HexColor("#B12525")
AMBER       = HexColor("#A56B16")

FONTS_DIR = r"C:\Users\Admin\AppData\Local\Microsoft\Windows\Fonts"
try:
    pdfmetrics.registerFont(TTFont("PBlack", f"{FONTS_DIR}\\Pretendard-Black.ttf"))
    pdfmetrics.registerFont(TTFont("PExtraBold", f"{FONTS_DIR}\\Pretendard-ExtraBold.ttf"))
    pdfmetrics.registerFont(TTFont("PBold", f"{FONTS_DIR}\\Pretendard-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("PSemi", f"{FONTS_DIR}\\Pretendard-SemiBold.ttf"))
    pdfmetrics.registerFont(TTFont("PMed", f"{FONTS_DIR}\\Pretendard-Medium.ttf"))
    pdfmetrics.registerFont(TTFont("PReg", f"{FONTS_DIR}\\Pretendard-Regular.ttf"))
except:
    # 폰트가 없을 경우 기본 폰트로 대체하기 위해 시스템 맑은 고딕 사용
    pdfmetrics.registerFont(TTFont("PBlack", "C:/Windows/Fonts/malgunbd.ttf"))
    pdfmetrics.registerFont(TTFont("PExtraBold", "C:/Windows/Fonts/malgunbd.ttf"))
    pdfmetrics.registerFont(TTFont("PBold", "C:/Windows/Fonts/malgunbd.ttf"))
    pdfmetrics.registerFont(TTFont("PSemi", "C:/Windows/Fonts/malgunbd.ttf"))
    pdfmetrics.registerFont(TTFont("PMed", "C:/Windows/Fonts/malgun.ttf"))
    pdfmetrics.registerFont(TTFont("PReg", "C:/Windows/Fonts/malgun.ttf"))

def rr(c, x, y, w, h, r, fill=None, stroke=None, lw=0.5):
    c.saveState()
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=bool(fill), stroke=bool(stroke))
    c.restoreState()

def create_cover():
    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    W, H = A4

    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    half = W / 2
    c.setLineWidth(4)
    c.setStrokeColor(ACCENT)
    c.line(0, H - 2, half, H - 2)
    c.setStrokeColor(BURGUNDY)
    c.line(half, H - 2, W, H - 2)
    c.setStrokeColor(BORDER_STR)
    c.setLineWidth(2)
    c.line(0, 1, W, 1)

    cx = W / 2
    top = H - 32 * mm

    tag_text = "GAME ANALYTICS PORTFOLIO"
    c.setFont("PBold", 8.5)
    c.setFillColor(ACCENT)
    tw = c.stringWidth(tag_text, "PBold", 8.5)
    tag_w = tw + 20
    tag_h = 20
    tag_x = cx - tag_w / 2
    tag_y = top
    rr(c, tag_x, tag_y, tag_w, tag_h, 10, fill=Color(0, 0.28, 0.73, alpha=0.06), stroke=Color(0, 0.28, 0.73, alpha=0.2), lw=0.6)
    c.drawCentredString(cx, tag_y + 6, tag_text)

    title_y = top - 22
    c.setFont("PBlack", 28)
    c.setFillColor(TEXT_DARK)
    c.drawCentredString(cx, title_y, "P의 거짓 (Lies of P)")

    c.setFont("PExtraBold", 20)
    c.setFillColor(TEXT_SUB)
    c.drawCentredString(cx, title_y - 28, "AI 리뷰데이터 분석 대시보드")

    rule_y = title_y - 48
    rule_w = 25
    c.setStrokeColor(BORDER_STR)
    c.setLineWidth(0.5)
    c.line(cx - rule_w, rule_y, cx + rule_w, rule_y)

    c.setFont("PSemi", 10)
    c.setFillColor(TEXT_MUTE)
    c.drawCentredString(cx, rule_y - 16, "PROTOTYPE  ·  2026")

    img_margin_x = 18 * mm
    img_top_y = rule_y - 30

    try:
        img = PILImage.open(COVER_IMAGE)
        iw, ih = img.size
        target_w = W - 2 * img_margin_x
        scale = target_w / iw
        target_h = ih * scale

        max_h = H * 0.52
        if target_h > max_h:
            target_h = max_h
            scale = target_h / ih
            target_w = iw * scale

        img_x = (W - target_w) / 2
        img_y = img_top_y - target_h

        card_pad = 1
        rr(c, img_x - card_pad, img_y - card_pad, target_w + card_pad * 2, target_h + card_pad * 2 + 20, 8, fill=CARD_BG, stroke=BORDER_STR, lw=0.6)

        bar_h = 18
        bar_y = img_y + target_h + card_pad
        c.saveState()
        c.setFillColor(GHOST_FILL)
        c.rect(img_x - card_pad + 0.5, bar_y, target_w + card_pad * 2 - 1, bar_h, fill=1, stroke=0)
        dot_r = 3.5
        dot_y_center = bar_y + bar_h / 2
        dot_start_x = img_x + 8
        for i, color in enumerate([RED, AMBER, GREEN]):
            c.setFillColor(color)
            c.circle(dot_start_x + i * 12, dot_y_center, dot_r, fill=1, stroke=0)
        c.setStrokeColor(BORDER_STR)
        c.setLineWidth(0.3)
        c.line(img_x - card_pad, bar_y, img_x + target_w + card_pad, bar_y)
        c.restoreState()

        c.drawImage(COVER_IMAGE, img_x, img_y, width=target_w, height=target_h, preserveAspectRatio=True, anchor='nw', mask='auto')

        pill_y = img_y - 14 * mm
    except Exception as e:
        print(f"Image load error: {e}")
        pill_y = img_top_y - 200

    pill_h = 11 * mm
    pill_gap = 5 * mm
    pill_data = [
        ("플랫폼", "Steam PC", ACCENT),
        ("장르", "소울라이크 액션", GREEN),
        ("분석 대상", "유저 리뷰 데이터", GREEN),
    ]
    total_pill_w = W - 2 * 18 * mm
    pill_w = (total_pill_w - 2 * pill_gap) / 3

    for i, (label, value, color) in enumerate(pill_data):
        px = 18 * mm + i * (pill_w + pill_gap)
        py = pill_y

        rr(c, px, py, pill_w, pill_h, 6, fill=CARD_BG, stroke=BORDER_STR, lw=0.5)

        c.saveState()
        c.setFillColor(color)
        c.rect(px + 1.5, py + 2, 2.5, pill_h - 4, fill=1, stroke=0)
        c.restoreState()

        c.setFont("PBold", 7)
        c.setFillColor(TEXT_MUTE)
        c.drawString(px + 10, py + pill_h - 10, label)

        c.setFont("PExtraBold", 11)
        c.setFillColor(color)
        c.drawString(px + 10, py + 4, value)

    c.setFont("PMed", 8)
    c.setFillColor(TEXT_MUTE)
    c.drawCentredString(cx, 16 * mm, "Steam Storefront API  ·  FastAPI  ·  SQLite  ·  Gemini 2.0 Flash  ·  Chart.js")

    c.setFont("PBold", 9)
    c.setFillColor(TEXT_SUB)
    c.drawCentredString(cx, 10 * mm, "조경환")

    c.showPage()
    c.save()

if __name__ == "__main__":
    create_cover()
    print(f"Created {OUTPUT_PDF}")
