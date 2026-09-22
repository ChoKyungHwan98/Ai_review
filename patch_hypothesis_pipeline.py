import os, re
from config import cfg

# ==========================================
# 1. Patch main.py to add /api/generate-hypothesis
# ==========================================
main_path = os.path.join(cfg.PROGRAM_DIR, "main.py")
with open(main_path, "r", encoding="utf-8") as f:
    main_code = f.read()

hypothesis_endpoint = """
@app.post("/api/generate-hypothesis", summary="포트폴리오 가설 요약 (PPT용)", include_in_schema=False)
def api_generate_hypothesis(payload: dict):
    \"\"\"게임 기획자의 시각에서 문제 원인 가설을 PPT 형태로 도출합니다.\"\"\"
    import httpx
    app_id    = str(payload.get("app_id", ""))
    game_name = payload.get("game_name", "Unknown Game")
    force     = payload.get("force", False)
    model     = payload.get("model", "google/gemini-2.0-flash-001")

    ins_path = cfg.project_file("insights_v4.json", int(app_id)) if app_id else cfg.INSIGHTS_JSON
    if not os.path.exists(ins_path):
        raise HTTPException(status_code=404, detail="insights_v4.json 없음")

    with open(ins_path, "r", encoding="utf-8") as f:
        ins = json.load(f)

    if not force and ins.get("llm_hypothesis"):
        return {"cached": True, "hypothesis": ins["llm_hypothesis"]}

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or "여기에" in api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY 미설정")

    system = ("당신은 시니어 게임 기획자이자 포트폴리오 멘토입니다. "
              "단순한 통계의 나열이 아니라, '왜 이런 결과가 나왔는지'에 대한 게임 기획적인 가설(Hypothesis)을 세우고, "
              "면접관을 설득할 수 있는 포트폴리오용 1페이지 요약(PPT 스타일)을 작성하세요. "
              "반드시 JSON 포맷만 반환해야 합니다.")
    
    user = (
        _build_insights_prompt(ins, game_name) +
        "\\n\\n위 데이터를 바탕으로, 이 게임의 핵심 문제점과 원인에 대한 '기획적 가설'을 세워주세요.\\n"
        "예: '액션의 타격감을 살리기 위해 모션 딜레이를 길게 가져간 것이, 역으로 유저들에게는 답답한 전투 템포로 인식되어 호불호가 강하게 갈리고 있다.'\\n"
        "아래 JSON 형식으로만 응답하세요:\\n"
        '{"title": "이 게임의 핵심 기획 가설 요약 (20자 이내)", '
        '"hypotheses": [ '
        '  { "issue": "발견된 현상(예: 전투 불호 의견 65%)", '
        '    "hypothesis": "기획적 원인 분석 가설(예: 묵직한 액션이 느린 템포로 체감됨)", '
        '    "design_proposal": "기획적 개선안(예: 회피 캔슬 프레임 완화)" } '
        ']}\\n'
        "hypotheses 배열은 가장 중요한 가설 2~3개만 작성하세요."
    )

    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                  "temperature": 0.4, "max_tokens": 800,
                  "response_format": {"type": "json_object"}},
            timeout=45.0,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:400])
        j = r.json()
        parsed = json.loads(j["choices"][0]["message"]["content"])

        ins["llm_hypothesis"] = {
            "title": parsed.get("title", "포트폴리오 핵심 가설"),
            "hypotheses": parsed.get("hypotheses", [])
        }
        with open(ins_path, "w", encoding="utf-8") as f:
            json.dump(ins, f, ensure_ascii=False, indent=2)

        return {"cached": False, "hypothesis": ins["llm_hypothesis"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""

if "api_generate_hypothesis" not in main_code:
    main_code = main_code.replace("# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n#  파이프라인 API", hypothesis_endpoint + "\n# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n#  파이프라인 API")
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main_code)
    print("main.py updated with new hypothesis endpoint.")
else:
    print("main.py already has the endpoint.")


# ==========================================
# 2. Patch dashboard.html to add Hypothesis Tab
# ==========================================
dash_path = os.path.join(cfg.PROGRAM_DIR, "static", "dashboard.html")
with open(dash_path, "r", encoding="utf-8") as f:
    dash_code = f.read()

# Add Sidebar Tab
if 'data-page="hypothesis"' not in dash_code:
    dash_code = dash_code.replace(
        '<button class="nav-item" data-page="insights" onclick="navTo(this)">AI 인사이트</button>',
        '<button class="nav-item" data-page="insights" onclick="navTo(this)">AI 인사이트</button>\n      <button class="nav-item" data-page="hypothesis" onclick="navTo(this)" style="color: #3182F6; font-weight: 700;">★ 기획 가설 (포트폴리오)</button>'
    )

# Add Hypothesis Page HTML
if 'id="hypothesis"' not in dash_code:
    hypothesis_html = """
    <!-- 기획 가설 (포트폴리오) 탭 -->
    <section id="hypothesis" class="page">
      <div class="toolbar" style="background:#F0F4FA; border-color:#83C3FF;">
        <div>
          <div style="font-size:18px; font-weight:700; color:#1B64DA; margin-bottom:4px;">포트폴리오 1-Page 요약 생성기</div>
          <div style="font-size:14px; color:#333D4B;">단순한 수치를 넘어, 기획자의 시선으로 "왜 그런 문제가 발생했는지" 가설을 세워줍니다. (PPT 형태로 출력)</div>
        </div>
        <button class="primary-btn" onclick="generateHypothesis()" id="btnHypo">💡 기획 가설 생성하기</button>
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
    # Insert right before </main> or after </section>
    dash_code = dash_code.replace("</main>", hypothesis_html + "\n  </main>")

# Add Hypothesis JS
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
      body: JSON.stringify({ app_id: CURRENT_APP_ID, game_name: document.getElementById('topGameName').textContent })
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
    <div style="background:#FFFFFF; border-radius:16px; border:1px solid var(--color-steel-border); padding:32px; box-shadow:0 4px 16px rgba(0,0,0,0.04); position:relative; overflow:hidden;">
      <div style="position:absolute; top:0; left:0; width:6px; height:100%; background:var(--color-electric-blue);"></div>
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

if "generateHypothesis(" not in dash_code:
    dash_code = dash_code.replace("/* --- 초기화 --- */", hypothesis_js + "\n/* --- 초기화 --- */")

    # Also render if already exists
    render_patch = """
  // LLM 인사이트 렌더링
  if (D.llm_insights) renderInsights(D.llm_insights.key_findings, D.llm_insights.recommendations, D.llm_insights);
  if (D.llm_hypothesis) renderHypothesis(D.llm_hypothesis);
"""
    dash_code = dash_code.replace("if (D.llm_insights) renderInsights(D.llm_insights.key_findings, D.llm_insights.recommendations, D.llm_insights);", render_patch)

    with open(dash_path, "w", encoding="utf-8") as f:
        f.write(dash_code)
    print("dashboard.html updated with Hypothesis tab.")
else:
    print("dashboard.html already has Hypothesis logic.")
