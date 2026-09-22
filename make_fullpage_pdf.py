import io
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import sys

def create_fullpage_pdf():
    IMAGE_PATH = r"C:\Users\Admin\.gemini\antigravity\brain\9deba450-15a6-4014-af9f-252bb03733e6\full_dashboard_1780499038324.png"
    OUTPUT_PDF = r"c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\P의거짓_포트폴리오_풀화면.pdf"
    
    # A4 size in points
    W, H = A4
    
    # Create canvas
    c = canvas.Canvas(OUTPUT_PDF, pagesize=A4)
    
    try:
        img = PILImage.open(IMAGE_PATH)
        iw, ih = img.size
        
        # We want to fill the A4 page. 
        # Calculate scale to fit width and scale to fit height
        scale_w = W / iw
        scale_h = H / ih
        
        # To "fill" the page as much as possible while maintaining aspect ratio,
        # we can use the minimum of both scales so the whole image is visible,
        # or just squeeze it slightly if they want it exactly filled.
        # Given "a4 한장에 다 채워도 돼", fitting within the page is safest.
        scale = min(scale_w, scale_h)
        
        target_w = iw * scale
        target_h = ih * scale
        
        # Center on page
        x = (W - target_w) / 2
        y = (H - target_h) / 2
        
        # Draw image
        c.drawImage(IMAGE_PATH, x, y, width=target_w, height=target_h, preserveAspectRatio=True)
        c.showPage()
        c.save()
        print(f"Successfully generated {OUTPUT_PDF}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_fullpage_pdf()
