import re

with open("static/dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Inject HTML
hypothesis_html = """
    <!-- 기획 가설 (포트폴리오) 탭 -->
    <section id="hypothesis" class="page">
      <div class="toolbar" style="background:#F0F4FA; border-color:#83C3FF;">
        <div>
          <div style="font-size:18px; font-weight:700; color:#1B64DA; margin-bottom:4px;">포트폴리오 1-Page 요약 생성기</div>
          <div style="font-size:14px; color:#333D4B;">단순한 수치를 넘어, 기획자의 시선으로 "왜 그런 문제가 발생했는지" 가설을 세워줍니다. (PPT 형태로 출력)</div>
        </div>
        <button class="primary-btn" onclick="generateHypothesis()" id="btnHypo" style="padding:12px 24px; font-size:16px; font-weight:bold; cursor:pointer;">💡 기획 가설 생성하기</button>
      </div>
      <div id="hypoContent" style="display:flex; flex-direction:column; gap:20px; display:none;">
        <div class="hero" style="background:#FFFFFF; border:2px solid #3182F6; box-shadow:0 12px 32px rgba(49,130,246,0.1);">
          <div style="font-size:14px; font-weight:700; color:#3182F6; margin-bottom:8px;">EXECUTIVE SUMMARY</div>
          <h2 id="hypoTitle" style="font-size:28px; font-weight:800; color:#191F28; margin:0; line-height:1.4;"></h2>
        </div>
        <div id="hypoCards" style="display:grid; grid-template-columns:1fr; gap:24px;"></div>
      </div>
    </section>
"""
if 'id="hypothesis"' not in content:
    content = content.replace("<script>", hypothesis_html + "\n\n<script>")

# 2. Inject Javascript
hypothesis_js = """
// ── 포트폴리오 가설 생성 ──
async function generateHypothesis() {
  const btn = document.getElementById('btnHypo');
  const orgText = btn.innerHTML;
  btn.innerHTML = '가설 생성 중... ⏳';
  btn.disabled = true;

  try {
    const r = await fetch('/api/generate-hypothesis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: currentAppId, game_name: ALL_GAMES.find(g => g.app_id === currentAppId)?.name || 'Game' })
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || '가설 생성 실패');
    }
    const data = await r.json();
    renderHypothesis(data.hypothesis);
  } catch(e) {
    alert(e.message);
  } finally {
    btn.innerHTML = orgText;
    btn.disabled = false;
  }
}

function renderHypothesis(h) {
  if (!h || !h.hypotheses) return;
  document.getElementById('hypoContent').style.display = 'flex';
  document.getElementById('hypoTitle').textContent = h.title;
  
  const cards = h.hypotheses.map((item, idx) => `
    <div style="background:#FFFFFF; border-radius:16px; border:1px solid #E5E8EB; padding:32px; box-shadow:0 4px 16px rgba(0,0,0,0.04); position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; width:6px; height:100%; background:#3182F6;"></div>
      <div style="display:grid; grid-template-columns:300px 1fr; gap:32px; align-items:start;">
        
        <div>
          <div style="font-size:12px; font-weight:700; color:#8B95A1; margin-bottom:4px;">OBSERVATION (발견된 현상)</div>
          <div style="font-size:18px; font-weight:700; color:#F04452; line-height:1.4;">${item.issue}</div>
        </div>
        
        <div style="display:flex; flex-direction:column; gap:20px;">
          <div>
            <div style="font-size:12px; font-weight:700; color:#8B95A1; margin-bottom:6px;">HYPOTHESIS (기획적 원인 분석)</div>
            <div style="font-size:16px; font-weight:600; color:#191F28; background:#F2F4F6; padding:16px; border-radius:12px; line-height:1.6;">
              🤔 ${item.hypothesis}
            </div>
          </div>
          
          <div>
            <div style="font-size:12px; font-weight:700; color:#8B95A1; margin-bottom:6px;">DESIGN PROPOSAL (기획 개선안)</div>
            <div style="font-size:16px; font-weight:600; color:#05C072; line-height:1.6; padding:0 8px;">
              ✨ ${item.design_proposal}
            </div>
          </div>
        </div>

      </div>
    </div>
  `).join('');
  document.getElementById('hypoCards').innerHTML = cards;
}
"""

if "function generateHypothesis()" not in content:
    # Inject it right after `let ALL_GAMES = [];`
    content = content.replace("let ALL_GAMES = [];", "let ALL_GAMES = [];\n" + hypothesis_js)

# 3. Add to load(appId) so it auto-renders if cached
if "function load(" in content and "renderHypothesis" not in content.split("function load(")[1]:
    # It renders in `if (D.key_findings)` block maybe?
    # Let's just find the end of `fetch` inside load()
    # Actually, we can just replace `document.getElementById('execTitle').textContent = ` to inject it
    content = content.replace("if (llm && llm.key_findings && llm.key_findings.length) {", 
                              "if (D.llm_hypothesis) { renderHypothesis(D.llm_hypothesis); } else { document.getElementById('hypoContent').style.display = 'none'; }\n    if (llm && llm.key_findings && llm.key_findings.length) {")

with open("static/dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Dashboard HTML fixed.")
