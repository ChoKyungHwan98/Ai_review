"""이모지 이스케이프를 실제 유니코드 문자로 변환"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

# JS에서 \\u 이스케이프가 아닌 실제 문자로
replacements = {
    '\\\\ud83c\\\\udfae': '🎮',
    '\\\\uc0c8 \\\\uac8c\\\\uc784 \\\\ubd84\\\\uc11d \\\\ucd94\\\\uac00': '새 게임 분석 추가',
    '\\\\uff0b': '＋',
}

for old, new in replacements.items():
    if old in content:
        content = content.replace(old, new)
        print(f'Replaced: {old[:30]} -> {new}')
    else:
        print(f'Not found: {old[:30]}')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)
print('Saved OK')
