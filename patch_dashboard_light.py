import re

with open("static/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update CSS Variables (Midnight -> Toss Light)
css_root_old = r""":root \{
  /\* ── Colors \(OpenSea 원본 Midnight Dark Theme\) ── \*/
  --color-midnight-ink:    #080809;     /\* page bg \*/
  --color-deep-graphite:   #141415;     /\* nav/panel bg \*/
  --color-slate-card:      #1b1d1f;     /\* card bg \*/
  --color-steel-border:    #26272d;     /\* borders \*/
  --color-soft-stone:      #34353c;     /\* strong borders \*/
  --color-ghost-fill:      #3c3d40;     /\* ghost surfaces \*/
  --color-white-canvas:    #ffffff;     /\* primary text \*/
  --color-silver-whisper:  #acadae;     /\* secondary text \*/
  --color-mute-whisper:    #71717a;     /\* muted text \*/
  --color-electric-blue:   #83c3ff;     /\* accent \*/
  --color-electric-blue-2: #6ab0f0;
  --color-success-green:   #47bb64;     /\* positive \*/
  --color-error-red:       #e24756;     /\* negative \*/
  --color-warn-amber:      #e5a93d;
  --color-burgundy:        #cf4060;"""

css_root_new = """:root {
  /* ── Colors (Toss Light Theme) ── */
  --color-midnight-ink:    #F2F4F6;     /* page bg */
  --color-deep-graphite:   #FFFFFF;     /* nav/panel bg */
  --color-slate-card:      #FFFFFF;     /* card bg */
  --color-steel-border:    #E5E8EB;     /* borders */
  --color-soft-stone:      #D1D6DB;     /* strong borders */
  --color-ghost-fill:      #F9FAFB;     /* ghost surfaces */
  --color-white-canvas:    #191F28;     /* primary text */
  --color-silver-whisper:  #333D4B;     /* secondary text */
  --color-mute-whisper:    #8B95A1;     /* muted text */
  --color-electric-blue:   #3182F6;     /* accent */
  --color-electric-blue-2: #1B64DA;
  --color-success-green:   #05C072;     /* positive */
  --color-error-red:       #F04452;     /* negative */
  --color-warn-amber:      #FF8C00;
  --color-burgundy:        #F04452;"""
content = re.sub(css_root_old, css_root_new, content)

# Update background color property to not use the wrong contrast
content = content.replace("background-color: var(--color-midnight-ink);", "background: var(--color-midnight-ink);")
content = content.replace("color: var(--color-white-canvas);", "color: var(--color-white-canvas);")

# Update box shadows to be softer for light theme
content = content.replace("--shadow-card:  rgba(255,255,255,0.08) 0px 0px 0px 1px inset;", "--shadow-card: 0 4px 16px rgba(0,0,0,0.04);")
content = content.replace("--shadow-hover: rgba(255,255,255,0.12) 0px 0px 0px 1px inset;", "--shadow-hover: 0 8px 24px rgba(0,0,0,0.08);")
content = content.replace("--shadow-hero:  rgba(255,255,255,0.06) 0px 0px 0px 1px inset, rgba(0,0,0,0.03) 0px 1px 2px 0px;", "--shadow-hero: 0 12px 32px rgba(0,0,0,0.1);")


# 2. Replace Sidebar CSS
sidebar_css_old = r"""/\* ── Left Sidebar ── \*/.*?/\* ── Right Content Area ── \*/"""
sidebar_css_new = """/* ── Left Sidebar (Toss Style) ── */
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 240px;
  background: var(--color-deep-graphite);
  border-right: 1px solid var(--color-steel-border);
  display: flex; flex-direction: column;
  padding: 28px 12px;
  z-index: 60;
  user-select: none;
}
.sidebar-brand {
  display: flex; align-items: center; gap: 10px;
  font-size: 17px; font-weight: 700; color: var(--color-white-canvas);
  padding: 0 12px; margin-bottom: 36px; text-decoration: none;
}
.sidebar-brand .dot {
  width: 28px; height: 28px; background: var(--color-electric-blue); border-radius: 8px;
  display: flex; align-items: center; justify-content: center; margin: 0;
}
.sidebar-nav { display: flex; flex-direction: column; gap: 4px; }
.nav-label {
  font-size: 11px; font-weight: 600; color: var(--color-mute-whisper);
  letter-spacing: .06em; text-transform: uppercase; padding: 0 14px; margin-bottom: 6px; margin-top: 12px;
}
.sidebar-tab {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 14px; border-radius: 12px;
  font-size: 14px; font-weight: 500; color: var(--color-silver-whisper);
  background: transparent; border: none; cursor: pointer; transition: background .15s, color .15s; width: 100%; text-align: left;
}
.sidebar-tab:hover { background: var(--color-midnight-ink); color: var(--color-white-canvas); }
.sidebar-tab.active { background: var(--color-midnight-ink); color: var(--color-white-canvas); font-weight: 600; }
.sidebar-tab svg { flex-shrink: 0; opacity: .6; }
.sidebar-tab.active svg { opacity: 1; }

.sidebar-footer { margin-top: auto; padding-top: 16px; border-top: 1px solid var(--color-steel-border); }

/* ── Right Content Area ── */"""
content = re.sub(sidebar_css_old, sidebar_css_new, content, flags=re.DOTALL)

# Adjust main wrap margin
content = content.replace("margin-left: 60px;", "margin-left: 240px;")

# 3. Replace Sidebar HTML
sidebar_html_old = r"""<!-- Sidebar -->
  <aside class="sidebar">
    <a href="#" class="sidebar-brand">RA</a>
    <nav class="sidebar-nav">
      <!-- 프로젝트 탭 아이콘 -->
      <button class="sidebar-tab active">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
        <span class="sidebar-tooltip">프로젝트</span>
      </button>
      
      <div class="sidebar-divider"></div>
      
      <!-- API Key 설정 (새로운 모달 트리거) -->
      <button class="sidebar-tab" onclick="openApiKeyModal()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
        <span class="sidebar-tooltip">API Key 관리</span>
      </button>
    </nav>
  </aside>"""

sidebar_html_new = """<!-- Sidebar -->
  <aside class="sidebar">
    <a href="/" class="sidebar-brand">
      <div class="dot">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
      </div>
      Review Analytics
    </a>
    
    <nav class="sidebar-nav">
      <div class="nav-label">프로젝트 관리</div>
      <button class="sidebar-tab" onclick="window.location.href='/'">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
        전체 프로젝트
      </button>
      <button class="sidebar-tab active">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>
        대시보드
      </button>
    </nav>

    <div class="sidebar-footer">
      <button class="sidebar-tab" onclick="openApiKeyModal()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path></svg>
        API Key 관리
      </button>
    </div>
  </aside>"""
content = content.replace(sidebar_html_old, sidebar_html_new)

# 4. Chart Colors Update (Since it's light theme, labels should be dark)
content = content.replace("color: '#acadae'", "color: '#8B95A1'")
content = content.replace("color: '#71717a'", "color: '#8B95A1'")
content = content.replace("color: '#ffffff'", "color: '#191F28'")

with open("static/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")
