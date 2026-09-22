import sys
sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

old = 'let DATA = {};\nlet currentAppId = 1623730;\n'
new = 'let DATA = {};\nlet currentAppId = 1623730;\nlet charts = {};\n'

if old in content:
    content = content.replace(old, new, 1)
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: Added let charts = {};')
else:
    print('ERROR: Target line not found!')
