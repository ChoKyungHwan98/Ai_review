import sys
sys.stdout.reconfigure(encoding='utf-8')

HTML_FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(HTML_FILE, encoding='utf-8-sig') as f:
    content = f.read()

lines = content.split('\n')
print(f'Original lines: {len(lines)}')

# 1963번 줄 (인덱스 1962)이 깨진 줄
# HTML 부분: <div class="kpi-sub">0 실패 (재시도로 모두 [깨진문자]
# JS 부분: if (isNaN(appId)) {  <- 이게 1963 줄 중간부터 시작됨

# 1962 인덱스 줄을 HTML만으로 복원
fixed_html_line = '          <div class="kpi-sub">0 실패 (재시도로 모두 성공)</div>'

# 삽입할 HTML 닫힘 태그들 + searchGame 함수 선언부
insert_block = [
    '          <div class="kpi-progress"><div id="usageCallsBar" style="width: 100%"></div></div>',
    '        </div>',
    '      </div>',
    '    </section>',
    '',
    '/* ============ Search ============ */',
    'let searchDropdown = null;',
    '',
    'function toggleSearch() {',
    "  const input = document.getElementById('searchInput');",
    '  input.focus();',
    "  input.value = '';",
    '}',
    '',
    'async function searchGame() {',
    "  const input = document.getElementById('searchInput');",
    '  const val = input.value.trim();',
    '  if (!val) return;',
    '',
    '  const appId = parseInt(val);',
]

# 1962 인덱스 이후의 JS 코드는 그대로 유지 (line 1963~: if (isNaN(appId)) 부터)
# 이 부분이 searchGame 함수의 나머지 바디가 됨
new_lines = lines[:1962] + [fixed_html_line] + insert_block + lines[1963:]

print(f'New lines: {len(new_lines)}')

# 검증
for i, l in enumerate(new_lines):
    if 'async function searchGame' in l or 'let searchDropdown' in l:
        print(f'  Found at line {i+1}: {l[:80]}')

# 저장 (UTF-8, BOM 없음)
with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))

print('Saved OK')

# 최종 검증
with open(HTML_FILE, encoding='utf-8') as f:
    final = f.read()
final_lines = final.split('\n')
print(f'Final file: {len(final_lines)} lines')
for i, l in enumerate(final_lines):
    if 'async function searchGame' in l:
        print(f'  searchGame at line {i+1}')
        # 전후 3줄 출력
        for j in range(max(0,i-1), min(len(final_lines), i+4)):
            print(f'    {j+1}: {final_lines[j][:100]}')
