import re

with open("static/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the Sidebar HTML completely
old_sidebar_pattern = r"<!-- ============ LEFT SIDEBAR.*?</aside>"
new_sidebar = """<!-- ============ LEFT SIDEBAR (Toss Style) ============ -->
  <aside class="sidebar" id="sidebar">
    <a href="/" class="sidebar-brand" style="margin-bottom: 32px;">
      <div class="dot" style="background:var(--color-electric-blue);">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
      </div>
      Data Console
    </a>
    
    <nav class="sidebar-nav">
      <div class="nav-label">프로젝트 탐색</div>
      <button class="sidebar-tab" onclick="window.location.href='/'">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
        홈으로 가기
      </button>

      <div class="nav-label" style="margin-top: 24px;">리뷰 분석 파이프라인</div>
      <button class="sidebar-tab active" data-page="overview" onclick="navTo(this)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"></rect><path d="M21 12H3"></path><path d="M12 3v18"></path></svg>
        대시보드
      </button>
      <button class="sidebar-tab" data-page="reviews" onclick="navTo(this)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
        리뷰 탐색
      </button>
      <button class="sidebar-tab" data-page="insights" onclick="navTo(this)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"></path></svg>
        AI 인사이트
      </button>
      <button class="sidebar-tab" data-page="sample" onclick="navTo(this)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.3 15.3a2.4 2.4 0 0 1 0 3.4l-2.6 2.6a2.4 2.4 0 0 1-3.4 0L2.7 8.7a2.41 2.41 0 0 1 0-3.4l2.6-2.6a2.41 2.41 0 0 1 3.4 0Z"></path><path d="m14.5 12.5 2-2"></path><path d="m11.5 9.5 2-2"></path><path d="m8.5 6.5 2-2"></path><path d="m17.5 15.5 2-2"></path></svg>
        표본 설계
      </button>
    </nav>

    <div class="sidebar-footer">
      <button class="sidebar-tab" data-page="system" onclick="navTo(this)">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        시스템 제어
      </button>
    </div>
  </aside>"""

content = re.sub(old_sidebar_pattern, new_sidebar, content, flags=re.DOTALL)

# 2. Fix Layout CSS & "요약" (Summary) Section Styling
# Remove the old left-border gradient from hero
content = content.replace(".hero::before {\n  content: '';\n  position: absolute; left: 0; top: 0; bottom: 0;\n  width: 4px;\n  background: linear-gradient(180deg, var(--color-electric-blue), var(--color-burgundy));\n}", "")

css_updates = {
    # Fix Sidebar Tooltip removal (since we now show text directly)
    ".sidebar-tab .sidebar-tooltip {": ".sidebar-tab .sidebar-tooltip { display: none !important; ",
    # Make hero (핵심 요약) look like a soft Toss card
    ".hero {\n  position: relative;\n  background: var(--color-ghost-fill);\n  border-radius: var(--radius-cards);\n  box-shadow: var(--shadow-hero);\n  padding: var(--spacing-16);\n  display: flex; gap: var(--spacing-16); align-items: flex-start;\n  margin-bottom: var(--spacing-24);\n  overflow: hidden;\n}": 
    ".hero {\n  position: relative;\n  background: #FFFFFF;\n  border-radius: 20px;\n  box-shadow: 0 4px 20px rgba(0,0,0,0.05);\n  padding: 32px;\n  display: flex; gap: 20px; flex-direction: column;\n  margin-bottom: 32px;\n  border: 1px solid var(--color-steel-border);\n}",
    # Make hero title larger
    ".hero-title {\n  font-size: var(--text-heading-sm); font-weight: var(--font-weight-medium);\n  margin: 0 0 var(--spacing-12);\n  line-height: var(--leading-heading-sm);\n  color: var(--color-white-canvas);\n}":
    ".hero-title {\n  font-size: 24px; font-weight: 700;\n  margin: 0 0 8px;\n  line-height: 1.4;\n  color: var(--color-white-canvas);\n}",
    # Make hero body text more readable
    ".hero-body {\n  color: var(--color-silver-whisper);\n  font-size: var(--text-body-sm); line-height: var(--leading-body-sm);\n  font-weight: var(--font-weight-regular);\n  max-width: 1100px;\n}":
    ".hero-body {\n  color: var(--color-silver-whisper);\n  font-size: 16px; line-height: 1.6;\n  font-weight: 500;\n  max-width: 1100px;\n}",
    # Adjust hero badge
    ".hero-badge {\n  font-family: var(--font-sans); font-size: var(--text-caption); font-weight: var(--font-weight-medium);\n  padding: var(--spacing-4) var(--spacing-12);\n  background: rgba(131, 195, 255, 0.08);\n  color: var(--color-electric-blue);\n  border: 1px solid rgba(131, 195, 255, 0.15);\n  border-radius: var(--radius-default);\n  display: inline-block; margin-bottom: var(--spacing-12);\n}":
    ".hero-badge {\n  font-family: var(--font-sans); font-size: 14px; font-weight: 700;\n  padding: 6px 12px;\n  background: rgba(49, 130, 246, 0.1);\n  color: var(--color-electric-blue);\n  border: none;\n  border-radius: 8px;\n  display: inline-block; margin-bottom: 0;\n}",
    
    # Improve Compare Cards (3-way recommendation comparison)
    ".compare-col {\n  padding: var(--card-padding);\n  background: var(--color-ghost-fill);\n  border-radius: var(--radius-cards);\n  box-shadow: var(--shadow-card);\n}":
    ".compare-col {\n  padding: 24px;\n  background: #FFFFFF;\n  border-radius: 16px;\n  box-shadow: 0 2px 12px rgba(0,0,0,0.03);\n  border: 1px solid var(--color-steel-border);\n}",
    
    # Page Title size
    ".page-title { margin: 0 0 var(--spacing-8); font-size: var(--text-display); font-weight: var(--font-weight-medium); line-height: var(--leading-display); }":
    ".page-title { margin: 0 0 12px; font-size: 28px; font-weight: 700; line-height: 1.3; color: var(--color-white-canvas); }",
    
    # Subtitle readability
    ".page-subtitle { font-size: var(--text-body-sm); color: var(--color-silver-whisper); margin-bottom: var(--section-gap); line-height: var(--leading-body-sm); }":
    ".page-subtitle { font-size: 16px; font-weight: 500; color: var(--color-mute-whisper); margin-bottom: 40px; line-height: 1.5; }",
    
    # Data Control Center Box polishing
    ".toolbar {\n  display: flex; justify-content: space-between; align-items: center;\n  background: var(--color-ghost-fill);\n  padding: var(--spacing-12) var(--spacing-16);\n  border-radius: var(--radius-cards);\n  margin-bottom: var(--spacing-24);\n}":
    ".toolbar {\n  display: flex; justify-content: space-between; align-items: center;\n  background: #F9FAFB;\n  padding: 20px 24px;\n  border-radius: 16px;\n  margin-bottom: 32px;\n  border: 1px solid var(--color-steel-border);\n}",
}

for old, new in css_updates.items():
    content = content.replace(old, new)

# 3. Increase sidebar spacing
content = content.replace("padding: 28px 12px;", "padding: 32px 16px;")
content = content.replace("padding: 11px 14px; border-radius: 12px;", "padding: 12px 16px; border-radius: 12px; font-size: 15px; margin-bottom: 4px;")

with open("static/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Dashboard polished.")
