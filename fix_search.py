"""dashboard.html의 Search 섹션을 완전히 재작성"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

# 현재 깨진 Search 섹션 찾기: "/* ============ Search" 부터 "/* ============ Load data" 까지
pattern = r'/\* =+ Search =+.*?(?=/\* =+ Load data =+)'
match = re.search(pattern, content, re.DOTALL)
if not match:
    print("ERROR: Search section not found")
    sys.exit(1)

print(f"Found Search section at char {match.start()}-{match.end()} ({match.end()-match.start()} chars)")

# 새 Search 섹션
NEW_SEARCH = r'''/* ============ Search ============ */
let searchDropdown = null;

function toggleSearch() {
  const input = document.getElementById('searchInput');
  input.focus();
  input.value = '';
}

async function searchGame() {
  const input = document.getElementById('searchInput');
  const val = input.value.trim();
  if (!val) return;

  const appId = parseInt(val);
  if (isNaN(appId)) {
    alert('숫자로 된 Steam App ID를 입력해주세요.\n예: 팰월드 = 1623730, CS2 = 730');
    return;
  }

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.textContent = '검색 중…';
  if (searchDropdown) { searchDropdown.remove(); searchDropdown = null; }

  try {
    const r = await fetch('/api/games/search?app_id=' + appId);
    if (!r.ok) {
      alert('App ID ' + appId + '를 찾을 수 없습니다.');
      return;
    }
    const game = await r.json();

    // 이미 분석된 게임인지 확인
    const gamesR = await fetch('/api/games');
    const gamesData = await gamesR.json();
    const existing = (gamesData.games || []).find(function(g) { return g.app_id === appId; });

    const bar = document.getElementById('searchBar');
    bar.style.position = 'relative';
    searchDropdown = document.createElement('div');
    searchDropdown.className = 'search-dropdown show';
    searchDropdown.style.maxWidth = '640px';

    // 게임 기본 정보
    let html = '<div style="padding:var(--spacing-16)">';
    html += '<div style="display:flex;align-items:center;gap:var(--spacing-12);margin-bottom:var(--spacing-12)">';
    html += '<img src="' + game.header_image + '" style="width:120px;height:45px;border-radius:var(--radius-default);object-fit:cover" />';
    html += '<div>';
    html += '<div style="font-weight:var(--font-weight-medium);font-size:var(--text-body-sm);color:var(--color-white-canvas)">' + game.name + '</div>';
    html += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">App ID: ' + game.app_id + ' · ' + (game.type || 'game') + '</div>';
    html += '</div>';
    if (existing) {
      html += '<button class="search-result-action" style="margin-left:auto" onclick="switchGame(' + appId + ');if(searchDropdown){searchDropdown.remove();searchDropdown=null;}">대시보드 보기</button>';
    }
    html += '</div>';

    // 리뷰 통계 로딩 영역
    html += '<div id="reviewStatsArea" style="border-top:1px solid var(--color-steel-border);padding-top:var(--spacing-12)">';
    html += '<div style="text-align:center;padding:var(--spacing-12);color:var(--color-mute-whisper);font-size:var(--text-caption)">📊 Steam 리뷰 통계 로딩 중…</div>';
    html += '</div></div>';

    searchDropdown.innerHTML = html;
    bar.appendChild(searchDropdown);

    // 리뷰 통계 비동기 로드
    try {
      const statsR = await fetch('/api/games/review-stats?app_id=' + appId);
      if (statsR.ok) {
        const st = await statsR.json();
        const kr = st.korean;
        const gl = st.global;
        const sd = st.sample_design;
        const statsArea = document.getElementById('reviewStatsArea');
        if (statsArea) {
          let sh = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--spacing-8);margin-bottom:var(--spacing-12)">';

          // 전체 리뷰
          sh += '<div style="background:var(--color-ghost-fill);padding:var(--spacing-8) var(--spacing-12);border-radius:var(--radius-default)">';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">🌍 전체 리뷰</div>';
          sh += '<div style="font-family:var(--font-mono);font-size:15px;color:var(--color-white-canvas);font-weight:var(--font-weight-medium)">' + gl.total.toLocaleString() + '건</div>';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">' + gl.score + '</div></div>';

          // 한국어 리뷰
          sh += '<div style="background:var(--color-ghost-fill);padding:var(--spacing-8) var(--spacing-12);border-radius:var(--radius-default)">';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">🇰🇷 한국어 리뷰</div>';
          sh += '<div style="font-family:var(--font-mono);font-size:15px;color:var(--color-white-canvas);font-weight:var(--font-weight-medium)">' + kr.total.toLocaleString() + '건</div>';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-success-green)">👍 ' + kr.positive.toLocaleString() + ' (' + kr.pos_rate + '%)  👎 ' + kr.negative.toLocaleString() + ' (' + kr.neg_rate + '%)</div></div>';

          // 필요 표본 ±5%
          sh += '<div style="background:var(--color-ghost-fill);padding:var(--spacing-8) var(--spacing-12);border-radius:var(--radius-default)">';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">📐 필요 표본 (±5%)</div>';
          sh += '<div style="font-family:var(--font-mono);font-size:15px;color:var(--color-white-canvas);font-weight:var(--font-weight-medium)">' + sd.sample_5pct.toLocaleString() + '건</div>';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">예상 비용: $' + sd.est_cost_5pct + '</div></div>';

          // 필요 표본 ±3%
          sh += '<div style="background:var(--color-ghost-fill);padding:var(--spacing-8) var(--spacing-12);border-radius:var(--radius-default)">';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">📐 필요 표본 (±3%)</div>';
          sh += '<div style="font-family:var(--font-mono);font-size:15px;color:var(--color-white-canvas);font-weight:var(--font-weight-medium)">' + sd.sample_3pct.toLocaleString() + '건</div>';
          sh += '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper)">예상 비용: $' + sd.est_cost_3pct + '</div></div>';

          sh += '</div>';

          // 하단 버튼 영역
          sh += '<div style="display:flex;gap:var(--spacing-8);justify-content:flex-end;padding-top:var(--spacing-8);border-top:1px solid var(--color-steel-border)">';
          if (existing) {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-success-green);display:flex;align-items:center;margin-right:auto">✅ 분석 완료된 게임</span>';
          } else {
            sh += '<span style="font-size:var(--text-caption);color:var(--color-mute-whisper);display:flex;align-items:center;margin-right:auto">모델: ' + sd.model + '</span>';
          }
          sh += '<button class="search-result-action" onclick="if(searchDropdown){searchDropdown.remove();searchDropdown=null;}" style="background:transparent;border:1px solid var(--color-steel-border);color:var(--color-silver-whisper)">닫기</button>';
          sh += '</div>';

          statsArea.innerHTML = sh;
        }
      }
    } catch(e2) {
      var sa = document.getElementById('reviewStatsArea');
      if (sa) sa.innerHTML = '<div style="font-size:var(--text-caption);color:var(--color-mute-whisper);padding:8px">리뷰 통계를 불러올 수 없습니다.</div>';
    }

    // 외부 클릭 시 닫기
    setTimeout(function() {
      document.addEventListener('click', function closeDD(e) {
        if (!bar.contains(e.target)) {
          if (searchDropdown) { searchDropdown.remove(); searchDropdown = null; }
          document.removeEventListener('click', closeDD);
        }
      });
    }, 100);
  } catch(e) {
    alert('검색 중 오류가 발생했습니다: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '검색';
  }
}

// Enter 키로 검색
document.getElementById('searchInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') searchGame();
});

async function startAnalysis(appId, gameName) {
  if (searchDropdown) { searchDropdown.remove(); searchDropdown = null; }
  document.getElementById('searchInput').value = '';

  try {
    const r = await fetch('/api/games');
    const data = await r.json();
    const existing = (data.games || []).find(function(g) { return g.app_id === appId; });
    if (existing) {
      switchGame(appId);
      return;
    }
  } catch(e) {}

  alert('"' + gameName + '" (App ID: ' + appId + ') 분석을 시작합니다.\n\n파이프라인이 백그라운드에서 실행됩니다.');

  try {
    const r = await fetch('/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app_id: appId })
    });
    if (r.ok) {
      const result = await r.json();
      if (result.status === 'done') {
        await loadGameTabs();
        switchGame(appId);
      }
    }
  } catch(e) {
    console.error('Pipeline error:', e);
  }
}

'''

content_new = content[:match.start()] + NEW_SEARCH + content[match.end():]
print(f"Original: {len(content)} chars -> New: {len(content_new)} chars")

# 검증
if 'async function searchGame()' in content_new and 'review-stats' in content_new:
    print("✅ searchGame found")
    print("✅ review-stats found")
else:
    print("❌ Verification failed")
    sys.exit(1)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content_new)
print("Saved OK")
