import sys

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the download button block in apilab with the downloads page and modal HTML
target_downloads = """      <!-- 데이터 다운로드 -->
      <div class="card" style="margin-bottom: var(--spacing-16)">
        <div class="section-head">
          <span class="accent-bar"></span>
          <span>데이터 다운로드</span>
        </div>
        <p class="tiny" style="margin: var(--spacing-4) 0 var(--spacing-16); color: var(--color-silver-whisper)">
          수집된 리뷰 원문과 AI 분석 결과를 CSV로 내려받을 수 있습니다
        </p>
        <div style="display: flex; gap: var(--spacing-12); flex-wrap: wrap;">
          <a href="/api/reviews/download?app_id=1623730" download
             style="display:inline-flex;align-items:center;gap:6px;padding:var(--spacing-8) var(--spacing-16);
                    background:var(--color-ghost-fill);border:1px solid var(--color-steel-border);
                    border-radius:var(--radius-default);color:var(--color-white-canvas);
                    text-decoration:none;font-size:var(--text-body-sm);font-weight:var(--font-weight-medium);
                    cursor:pointer;transition:background 0.2s">
            📥 리뷰 원문 CSV
          </a>
          <a href="/api/analysis/download?app_id=1623730" download
             style="display:inline-flex;align-items:center;gap:6px;padding:var(--spacing-8) var(--spacing-16);
                    background:var(--color-ghost-fill);border:1px solid var(--color-steel-border);
                    border-radius:var(--radius-default);color:var(--color-white-canvas);
                    text-decoration:none;font-size:var(--text-body-sm);font-weight:var(--font-weight-medium);
                    cursor:pointer;transition:background 0.2s">
            📊 AI 분석 결과 CSV
          </a>
        </div>
      </div>

</section>"""

replacement_downloads = """
      <!-- API 사용 현황 하단 여백 추가 -->
      <div style="margin-bottom: var(--spacing-16)"></div>
</section>

    <!-- 다운로드 페이지 -->
    <section class="page" data-page="downloads">
      <h1 class="title">데이터 다운로드</h1>
      <p class="subtitle">수집 및 AI 분석이 완료된 게임 데이터를 CSV로 내려받습니다</p>
      
      <div class="card" style="margin-top: var(--spacing-24)">
        <div class="section-head">
          <span class="accent-bar"></span>
          <span id="downloadGameTitle">Palworld (현재 활성화된 게임)</span>
        </div>
        <p class="tiny" style="margin: var(--spacing-8) 0 var(--spacing-24); color: var(--color-silver-whisper)">
          수집된 원문 텍스트 데이터와 감성/속성/카테고리가 라벨링된 AI 분석 결과를 Excel 또는 데이터 분석 툴에서 자유롭게 활용할 수 있도록 CSV 형식으로 내보냅니다.
        </p>
        
        <div style="display: flex; gap: var(--spacing-16); flex-wrap: wrap;">
          <a id="btnDownloadReviews" href="/api/reviews/download?app_id=1623730" download
             style="display:inline-flex;align-items:center;gap:8px;padding:var(--spacing-12) var(--spacing-24);
                    background:var(--color-ghost-fill);border:1px solid var(--color-steel-border);
                    border-radius:var(--radius-default);color:var(--color-white-canvas);
                    text-decoration:none;font-size:var(--text-body-sm);font-weight:var(--font-weight-medium);
                    cursor:pointer;transition:all 0.2s;box-shadow:var(--shadow-subtle)">
            📥 리뷰 원문 CSV 다운로드
          </a>
          <a id="btnDownloadAnalysis" href="/api/analysis/download?app_id=1623730" download
             style="display:inline-flex;align-items:center;gap:8px;padding:var(--spacing-12) var(--spacing-24);
                    background:var(--color-ghost-fill);border:1px solid var(--color-steel-border);
                    border-radius:var(--radius-default);color:var(--color-white-canvas);
                    text-decoration:none;font-size:var(--text-body-sm);font-weight:var(--font-weight-medium);
                    cursor:pointer;transition:all 0.2s;box-shadow:var(--shadow-subtle)">
            📊 AI 분석 결과 CSV 다운로드
          </a>
        </div>
      </div>
    </section>

  <!-- 분석 설정 및 실시간 진행 모달 -->
  <div id="pipelineModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:9999; align-items:center; justify-content:center;">
    <div class="card" style="width:100%; max-width:540px; background:var(--color-dark-void); border:1px solid var(--color-steel-border); padding:var(--spacing-24); position:relative; box-shadow:0 20px 40px rgba(0,0,0,0.5)">
      <h2 style="font-size:18px; margin-bottom:var(--spacing-8); color:var(--color-white-canvas)">🚀 신규 게임 리뷰 분석 설정</h2>
      <p class="tiny" style="color:var(--color-silver-whisper); margin-bottom:var(--spacing-16)">새로운 게임의 스팀 리뷰를 수집하고 AI 다차원 감성 및 모바일 이식성 분석을 시작합니다.</p>
      
      <!-- 설정 폼 -->
      <div id="pipelineSetupForm">
        <div style="margin-bottom:var(--spacing-16)">
          <label style="display:block; font-size:var(--text-caption); color:var(--color-mute-whisper); margin-bottom:4px">분석 대상 게임 App ID</label>
          <input type="text" id="modalAppId" disabled style="width:100%; background:var(--color-ghost-fill); border:1px solid var(--color-steel-border); color:var(--color-silver-whisper); padding:var(--spacing-8); border-radius:var(--radius-default)" />
        </div>
        
        <div style="margin-bottom:var(--spacing-16)">
          <label style="display:block; font-size:var(--text-caption); color:var(--color-mute-whisper); margin-bottom:6px">표본 오차 및 수집 크기 선택</label>
          <div style="display:flex; flex-direction:column; gap:8px">
            <label style="display:flex; align-items:center; gap:8px; padding:var(--spacing-8); border:1px solid var(--color-steel-border); border-radius:var(--radius-default); background:var(--color-ghost-fill); cursor:pointer">
              <input type="radio" name="modalSampleSize" id="opt5pct" checked />
              <div style="margin-left:8px">
                <div style="font-size:var(--text-body-sm); color:var(--color-white-canvas)">±5% 오차 표본 (<span id="modalS5Text">379</span>건 수집)</div>
                <div class="tiny" style="color:var(--color-silver-whisper)">예상 비용: $<span id="modalCost5Text">0.1</span> (Gemini 2.0 Flash)</div>
              </div>
            </label>
            <label style="display:flex; align-items:center; gap:8px; padding:var(--spacing-8); border:1px solid var(--color-steel-border); border-radius:var(--radius-default); background:var(--color-ghost-fill); cursor:pointer">
              <input type="radio" name="modalSampleSize" id="opt3pct" />
              <div style="margin-left:8px">
                <div style="font-size:var(--text-body-sm); color:var(--color-white-canvas)">±3% 오차 표본 (<span id="modalS3Text">1025</span>건 수집)</div>
                <div class="tiny" style="color:var(--color-silver-whisper)">예상 비용: $<span id="modalCost3Text">0.28</span> (Gemini 2.0 Flash)</div>
              </div>
            </label>
            <label style="display:flex; align-items:center; gap:8px; padding:var(--spacing-8); border:1px solid var(--color-steel-border); border-radius:var(--radius-default); background:var(--color-ghost-fill); cursor:pointer">
              <input type="radio" name="modalSampleSize" id="optCustom" />
              <div style="margin-left:8px; flex-grow:1; display:flex; align-items:center; gap:8px">
                <span style="font-size:var(--text-body-sm); color:var(--color-white-canvas); min-width:80px">커스텀 수집:</span>
                <input type="number" id="modalCustomSize" value="1000" style="width:100px; background:var(--color-dark-void); border:1px solid var(--color-steel-border); color:var(--color-white-canvas); padding:4px; border-radius:4px" />
                <span style="font-size:var(--text-body-sm); color:var(--color-white-canvas)">건</span>
              </div>
            </label>
          </div>
        </div>

        <div style="margin-bottom:var(--spacing-16)">
          <label style="display:block; font-size:var(--text-caption); color:var(--color-mute-whisper); margin-bottom:4px">분석 모델</label>
          <select id="modalModel" style="width:100%; background:var(--color-ghost-fill); border:1px solid var(--color-steel-border); color:var(--color-white-canvas); padding:var(--spacing-8); border-radius:var(--radius-default)">
            <option value="google/gemini-2.0-flash-001">google/gemini-2.0-flash-001 (기본 - 초고속 & 초저가)</option>
          </select>
        </div>

        <div style="display:flex; gap:var(--spacing-8); justify-content:flex-end; margin-top:var(--spacing-24)">
          <button class="search-result-action" onclick="closePipelineModal()" style="background:transparent; border:1px solid var(--color-steel-border); color:var(--color-silver-whisper)">취소</button>
          <button class="search-result-action" onclick="executePipelineRun()" style="background:var(--color-success-green); color:white; border:none">🚀 분석 파이프라인 가동</button>
        </div>
      </div>

      <!-- 실시간 진행 뷰 -->
      <div id="pipelineProgressView" style="display:none">
        <div style="text-align:center; margin-bottom:var(--spacing-16)">
          <div style="display:inline-block; font-size:24px; margin-bottom:8px">⚙️</div>
          <div style="font-weight:var(--font-weight-medium); color:var(--color-white-canvas)">스팀 리뷰 수집 및 AI 다차원 분석 가동 중…</div>
          <div class="tiny" style="color:var(--color-silver-whisper); margin-top:4px">백그라운드에서 6단계 파이프라인이 자동 실행되고 있습니다.</div>
        </div>

        <!-- 프로그레스 바 -->
        <div style="background:var(--color-ghost-fill); height:12px; border-radius:6px; overflow:hidden; margin-bottom:var(--spacing-24); border:1px solid var(--color-steel-border)">
          <div id="modalProgressBar" style="width:5%; height:100%; background:linear-gradient(90deg, var(--color-blue-electric), var(--color-success-green)); transition:width 0.4s ease-out"></div>
        </div>

        <!-- 단계별 상태 목록 -->
        <div style="display:flex; flex-direction:column; gap:var(--spacing-12); background:var(--color-ghost-fill); padding:var(--spacing-12); border-radius:var(--radius-default); border:1px solid var(--color-steel-border); margin-bottom:var(--spacing-16)">
          <div id="step_cost_estimate" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">💰 Step 0: 분석 비용 견적</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
          <div id="step_collect" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">📥 Step 1: 스팀 한국어 리뷰 수집</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
          <div id="step_analyze" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">🤖 Step 2: LLM 다차원 감성 분석</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
          <div id="step_quality" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">🔍 Step 3: 데이터셋 품질 평가</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
          <div id="step_verify" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">🎯 Step 4: AI 신뢰도 교차 검증</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
          <div id="step_insights" style="display:flex; justify-content:space-between; font-size:var(--text-body-sm)">
            <span style="color:var(--color-silver-whisper)">📊 Step 5: 인사이트 리포트 & 차트 생성</span>
            <span class="step-status" style="color:var(--color-mute-whisper)">대기 중</span>
          </div>
        </div>

        <div style="text-align:center">
          <span id="pipelineStatusText" style="font-size:var(--text-caption); color:var(--color-blue-electric); font-weight:var(--font-weight-medium)">초기화 중…</span>
        </div>
      </div>
    </div>
  </div>
"""

content = content.replace(target_downloads, replacement_downloads)

# 2. Add dynamic download fields update logic inside load(appId)
old_load_end = """  try { renderVerify(); } catch(e) { console.error('renderVerify error:', e); }
  try { renderSample(); } catch(e) { console.error('renderSample error:', e); }
}"""

new_load_end = """  try { renderVerify(); } catch(e) { console.error('renderVerify error:', e); }
  try { renderSample(); } catch(e) { console.error('renderSample error:', e); }

  // Update dynamic downloads URLs and game title
  try {
    const downloadReviewsBtn = document.getElementById('btnDownloadReviews');
    const downloadAnalysisBtn = document.getElementById('btnDownloadAnalysis');
    const downloadGameTitle = document.getElementById('downloadGameTitle');
    if (downloadReviewsBtn && downloadAnalysisBtn) {
      downloadReviewsBtn.href = `/api/reviews/download?app_id=${currentAppId}`;
      downloadAnalysisBtn.href = `/api/analysis/download?app_id=${currentAppId}`;
    }
    if (downloadGameTitle && DATA.game_name) {
      downloadGameTitle.textContent = `${DATA.game_name} (App ID: ${currentAppId})`;
    }
  } catch(e) { console.error('downloads update error:', e); }
}"""

content = content.replace(old_load_end, new_load_end)

# 3. Add analysis start triggers in searchGame result panel
old_btn_sh = """          sh += '<div style="display:flex;gap:var(--spacing-8);justify-content:flex-end;padding-top:var(--spacing-8);border-top:1px solid var(--color-steel-border)">';
          if (existing) {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-success-green);display:flex;align-items:center;margin-right:auto">✅ 분석 완료된 게임</span>';
          } else {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-mute-whisper);display:flex;align-items:center;margin-right:auto">모델: ' + sd.model + '</span>';
          }
          sh += '<button class="search-result-action" onclick="if(searchDropdown){searchDropdown.remove();searchDropdown=null;}" style="background:transparent;border:1px solid var(--color-steel-border);color:var(--color-silver-whisper)">닫기</button>';
          sh += '</div>';"""

new_btn_sh = """          sh += '<div style="display:flex;gap:var(--spacing-8);justify-content:flex-end;padding-top:var(--spacing-8);border-top:1px solid var(--color-steel-border);align-items:center">';
          if (existing) {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-success-green);display:flex;align-items:center;margin-right:auto">✅ 분석 완료된 게임</span>';
            sh += '<button class="search-result-action" onclick="switchGame(' + appId + ');if(searchDropdown){searchDropdown.remove();searchDropdown=null;}">대시보드 보기</button>';
          } else {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-mute-whisper);display:flex;align-items:center;margin-right:auto">모델: ' + sd.model + '</span>';
            sh += '<button class="search-result-action" onclick="startNewAnalysis(' + appId + ', ' + sd.sample_5pct + ', ' + sd.sample_3pct + ')" style="background:var(--color-blue-electric);color:white;border:none">🚀 분석 설계 & 시작</button>';
          }
          sh += '<button class="search-result-action" onclick="if(searchDropdown){searchDropdown.remove();searchDropdown=null;}" style="background:transparent;border:1px solid var(--color-steel-border);color:var(--color-silver-whisper)">닫기</button>';
          sh += '</div>';"""

content = content.replace(old_btn_sh, new_btn_sh)

# 4. Append pipeline controller javascript functions right before </script> at the end
js_pipeline_controllers = """
/* ============ New Dynamic Pipeline Flow ============ */
let pipelinePollInterval = null;

function startNewAnalysis(appId, s5, s3) {
  if (searchDropdown) {
    searchDropdown.remove();
    searchDropdown = null;
  }
  
  const modal = document.getElementById('pipelineModal');
  modal.style.display = 'flex';
  
  document.getElementById('modalAppId').value = appId;
  document.getElementById('modalS5Text').textContent = s5.toLocaleString();
  document.getElementById('modalS3Text').textContent = s3.toLocaleString();
  
  const costPerReview = 1100 * (0.10 + 0.40) / 2 / 1000000;
  document.getElementById('modalCost5Text').textContent = (s5 * costPerReview).toFixed(4);
  document.getElementById('modalCost3Text').textContent = (s3 * costPerReview).toFixed(4);
  
  document.getElementById('pipelineSetupForm').style.display = 'block';
  document.getElementById('pipelineProgressView').style.display = 'none';
}

function closePipelineModal() {
  const modal = document.getElementById('pipelineModal');
  modal.style.display = 'none';
  if (pipelinePollInterval) {
    clearInterval(pipelinePollInterval);
    pipelinePollInterval = null;
  }
}

async function executePipelineRun() {
  const appId = parseInt(document.getElementById('modalAppId').value);
  let sampleSize = 379;
  
  if (document.getElementById('opt5pct').checked) {
    sampleSize = parseInt(document.getElementById('modalS5Text').textContent.replace(/,/g, ''));
  } else if (document.getElementById('opt3pct').checked) {
    sampleSize = parseInt(document.getElementById('modalS3Text').textContent.replace(/,/g, ''));
  } else {
    sampleSize = parseInt(document.getElementById('modalCustomSize').value) || 1000;
  }
  
  const model = document.getElementById('modalModel').value;
  
  document.getElementById('pipelineSetupForm').style.display = 'none';
  document.getElementById('pipelineProgressView').style.display = 'block';
  
  try {
    const r = await fetch('/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_id: appId,
        lang: 'koreana',
        budget: 10.0
      })
    });
    
    if (!r.ok) {
      const err = await r.json();
      alert('파이프라인 실행 시작 오류: ' + (err.detail || r.statusText));
      closePipelineModal();
      return;
    }
    
    pollPipelineProgress(appId);
  } catch (e) {
    alert('파이프라인 서버 연결 실패: ' + e.message);
    closePipelineModal();
  }
}

function pollPipelineProgress(appId) {
  const bar = document.getElementById('modalProgressBar');
  const statusText = document.getElementById('pipelineStatusText');
  
  const stepCollect = document.querySelector('#step_collect .step-status');
  const stepAnalyze = document.querySelector('#step_analyze .step-status');
  const stepQuality = document.querySelector('#step_quality .step-status');
  const stepVerify  = document.querySelector('#step_verify .step-status');
  const stepInsights = document.querySelector('#step_insights .step-status');
  const stepCost    = document.querySelector('#step_cost_estimate .step-status');

  let pct = 5;
  bar.style.width = pct + '%';
  statusText.textContent = '비용 분석 견적 중…';

  pipelinePollInterval = setInterval(async () => {
    try {
      const r = await fetch('/pipeline/result');
      if (!r.ok) return;
      const res = await r.json();
      
      if (res.status === 'no_runs') return;
      
      const steps = res.steps || {};
      
      if (steps.cost_estimate) {
        stepCost.textContent = steps.cost_estimate.status === 'done' ? '✅ 완료' : steps.cost_estimate.status;
        stepCost.style.color = steps.cost_estimate.status === 'done' ? 'var(--color-success-green)' : 'var(--color-silver-whisper)';
        if (pct < 15) { pct = 15; bar.style.width = pct + '%'; }
      }
      
      if (steps.collect) {
        stepCollect.textContent = steps.collect.status === 'done' ? '✅ 완료' : steps.collect.status === 'skipped' ? '⏭️ 스킵됨' : '⚙️ 진행 중';
        stepCollect.style.color = steps.collect.status === 'done' ? 'var(--color-success-green)' : 'var(--color-blue-electric)';
        statusText.textContent = '스팀 한국어 리뷰 수집 중…';
        if (pct < 35) { pct = 35; bar.style.width = pct + '%'; }
      }
      
      if (steps.analyze) {
        stepAnalyze.textContent = steps.analyze.status === 'done' ? '✅ 완료' : '⚙️ 분석 중';
        stepAnalyze.style.color = steps.analyze.status === 'done' ? 'var(--color-success-green)' : 'var(--color-blue-electric)';
        statusText.textContent = 'AI 다차원 분석 실행 중 (수집된 리뷰 병렬 처리)…';
        if (pct < 65) { pct = 65; bar.style.width = pct + '%'; }
      }
      
      if (steps.quality) {
        stepQuality.textContent = steps.quality.status === 'done' ? '✅ 완료' : '⚙️ 점검 중';
        stepQuality.style.color = steps.quality.status === 'done' ? 'var(--color-success-green)' : 'var(--color-blue-electric)';
        statusText.textContent = '데이터셋 정량 품질 측정 중…';
        if (pct < 80) { pct = 80; bar.style.width = pct + '%'; }
      }
      
      if (steps.verify) {
        stepVerify.textContent = steps.verify.status === 'done' ? '✅ 완료' : '⚙️ 검증 중';
        stepVerify.style.color = steps.verify.status === 'done' ? 'var(--color-success-green)' : 'var(--color-blue-electric)';
        statusText.textContent = 'AI 신뢰성 크로스 검증 중…';
        if (pct < 90) { pct = 90; bar.style.width = pct + '%'; }
      }
      
      if (steps.insights) {
        stepInsights.textContent = steps.insights.status === 'done' ? '✅ 완료' : '⚙️ 생성 중';
        stepInsights.style.color = steps.insights.status === 'done' ? 'var(--color-success-green)' : 'var(--color-blue-electric)';
        statusText.textContent = '가중치 보정 및 대시보드 리포트 생성 중…';
        if (pct < 98) { pct = 98; bar.style.width = pct + '%'; }
      }
      
      if (res.status === 'done') {
        bar.style.width = '100%';
        statusText.textContent = '🎉 파이프라인 분석 완료!';
        statusText.style.color = 'var(--color-success-green)';
        clearInterval(pipelinePollInterval);
        
        setTimeout(async () => {
          closePipelineModal();
          await loadGameTabs();
          switchGame(appId);
        }, 1500);
      } else if (res.status === 'failed') {
        statusText.textContent = '❌ 파이프라인 오류: ' + (res.error || '실패');
        statusText.style.color = 'var(--color-neg-red)';
        clearInterval(pipelinePollInterval);
      }
      
    } catch(e) {
      console.error('Polling error:', e);
    }
  }, 1500);
}
"""

content = content.replace("})();\n</script>",js_pipeline_controllers + "\n})();\n</script>")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: dashboard.html fully patched with dynamic analysis & downloads page!")
