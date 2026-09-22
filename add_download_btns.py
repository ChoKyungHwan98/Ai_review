"""AI 분석 탭에 CSV 다운로드 버튼 추가"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

# API 사용 현황 섹션 뒤, </section> 닫힘 태그 앞에 다운로드 버튼 삽입
# "Steam API → FastAPI" 푸터 텍스트 앞에 삽입
DOWNLOAD_SECTION = '''
      <!-- 데이터 다운로드 -->
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

'''

marker = 'Steam API \u2192 FastAPI'
if marker in content:
    # 마커가 포함된 줄의 시작 위치에서 적절한 삽입 지점 찾기
    idx = content.find(marker)
    # 마커를 포함하는 <p> 시작 찾기
    p_start = content.rfind('<p', 0, idx)
    content = content[:p_start] + DOWNLOAD_SECTION + content[p_start:]
    
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: added download buttons before footer')
else:
    print('ERROR: footer marker not found')
    # 대안: </section> 바로 앞에 삽입
    last_section = content.rfind('</section>')
    if last_section >= 0:
        content = content[:last_section] + DOWNLOAD_SECTION + content[last_section:]
        with open(FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print('OK: added download buttons before last </section>')
