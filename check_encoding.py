import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, 'rb') as f:
    raw = f.read()

target = '데이터 다운로드'.encode('utf-8')
if target in raw:
    print('SUCCESS: "데이터 다운로드" exists as valid UTF-8 in the raw file!')
else:
    print('WARNING: "데이터 다운로드" NOT found as UTF-8 in raw bytes!')

# Let's inspect the last 1000 characters in raw bytes as decoded UTF-8 (ignoring errors)
try:
    text = raw.decode('utf-8')
    print('Successfully decoded file as UTF-8. Length:', len(text))
    
    # Check if there are duplicate or placeholder elements
    if '데이터 다운로드' in text:
        print('Found "데이터 다운로드" in text successfully.')
except Exception as e:
    print('Decoded failed:', e)
