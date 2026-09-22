"""누락된 navTo, loadGameTabs, switchGame 함수 추가"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

MISSING_FNS = """
/* ============ Navigation ============ */
function navTo(btn) {
  const p = btn.dataset.page;
  document.querySelectorAll('.sidebar-tab').forEach(function(t) { t.classList.toggle('active', t === btn); });
  document.querySelectorAll('section.page').forEach(function(s) { s.classList.toggle('active', s.dataset.page === p); });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ============ Game Tabs ============ */
async function loadGameTabs() {
  try {
    const r = await fetch('/api/games');
    const data = await r.json();
    const games = data.games || [];
    const container = document.getElementById('gameTabs');
    let html = '';
    for (let i = 0; i < games.length; i++) {
      const g = games[i];
      const cls = g.app_id === currentAppId ? 'active' : '';
      html += '<button class="game-tab ' + cls + '" data-appid="' + g.app_id + '" onclick="switchGame(' + g.app_id + ')">';
      html += '<span>\\ud83c\\udfae</span>';
      html += '<span>' + (g.name_kr || g.name) + '</span>';
      html += '</button>';
    }
    html += '<button class="game-tab-add" onclick="toggleSearch()" title="\\uc0c8 \\uac8c\\uc784 \\ubd84\\uc11d \\ucd94\\uac00">\\uff0b</button>';
    container.innerHTML = html;
  } catch(e) { console.error('loadGameTabs error:', e); }
}

function switchGame(appId) {
  currentAppId = appId;
  load(appId);
  loadGameTabs();
}

"""

marker = '/* ============ Search ============ */'
if marker in content:
    content = content.replace(marker, MISSING_FNS + marker, 1)
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: added navTo, loadGameTabs, switchGame')
else:
    print('ERROR: marker not found')

# Verify
for fn in ['function navTo', 'function switchGame', 'async function loadGameTabs']:
    if fn in content:
        print(f'  OK: {fn}')
    else:
        print(f'  MISSING: {fn}')
