import re

with open("static/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. EXACT CSS from index.html (with hex colors injected)
css_new = """/* ── Left Sidebar (Toss Style Exact) ── */
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 260px;
  background-color: #FFFFFF;
  border-right: 1px solid #E5E8EB;
  display: flex;
  flex-direction: column;
  padding: 24px 16px;
  z-index: 60;
  user-select: none;
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #191F28;
  margin-bottom: 40px;
  padding: 0 8px;
  cursor: pointer;
  text-decoration: none;
}
.brand-icon {
  color: #3182F6;
  display: flex;
  align-items: center;
}
.nav-group {
  margin-bottom: 24px;
}
.nav-label {
  font-size: 13px;
  font-weight: 600;
  color: #8B95A1;
  margin-bottom: 8px;
  padding: 0 8px;
}
.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-radius: 12px;
  color: #191F28;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
  text-decoration: none;
  margin-bottom: 4px;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
}
.nav-item:hover { background-color: #FAFAFA; }
.nav-item.active { background-color: #F2F4F6; font-weight: 600; }
.sidebar-bottom {
  margin-top: auto;
  border-top: 1px solid #E5E8EB;
  padding-top: 16px;
}
.bottom-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  font-size: 14px;
  color: #8B95A1;
  cursor: pointer;
  border-radius: 12px;
  transition: background-color 0.2s;
  border: none;
  background: transparent;
  width: 100%;
  text-align: left;
}
.bottom-item:hover { background-color: #FAFAFA; color: #191F28; }
/* ── Right Content Area ── */"""

css_old = r"/\* ── Left Sidebar ── \*/.*?/\* ── Right Content Area ── \*/"
content = re.sub(css_old, css_new, content, flags=re.DOTALL)


# 2. EXACT HTML from index.html
html_new = """<!-- ============ LEFT SIDEBAR ============ -->
  <aside class="sidebar" id="sidebar">
    <a href="/" class="sidebar-brand">
      <span class="brand-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
      </span>
      Data Console
    </a>
    
    <div class="nav-group">
      <div class="nav-label">프로젝트 관리</div>
      <button class="nav-item" onclick="window.location.href='/'">전체 프로젝트</button>
    </div>

    <div class="nav-group">
      <div class="nav-label">리뷰 분석 파이프라인</div>
      <button class="nav-item active" data-page="overview" onclick="navTo(this)">대시보드</button>
      <button class="nav-item" data-page="reviews" onclick="navTo(this)">리뷰 탐색</button>
      <button class="nav-item" data-page="insights" onclick="navTo(this)">AI 인사이트</button>
      <button class="nav-item" data-page="sample" onclick="navTo(this)">표본 설계</button>
    </div>

    <div class="sidebar-bottom">
      <button class="bottom-item" onclick="openApiKeyModal()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
        API Key 관리
      </button>
      <button class="bottom-item" data-page="system" onclick="navTo(this)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><circle cx="12" cy="12" r="4"></circle></svg>
        시스템 제어
      </button>
    </div>
  </aside>"""

html_old = r"<!-- ============ LEFT SIDEBAR ============ -->.*?</aside>"
content = re.sub(html_old, html_new, content, flags=re.DOTALL)

with open("static/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Sidebar synced exactly.")
