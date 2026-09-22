import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\static\dashboard.html'

with open(FILE, encoding='utf-8') as f:
    content = f.read()

# Sidebar buttons
print("=== SIDEBAR BUTTONS ===")
for m in re.finditer(r'<button[^>]*class="sidebar-tab[^>]*>.*?</button>', content, re.DOTALL):
    print(m.group().replace('\n', ' ').strip()[:150])

# Page sections
print("\n=== PAGE SECTIONS ===")
for m in re.finditer(r'<section[^>]*class="page[^>]*>.*?</section>', content, re.DOTALL):
    # Print only the start of the section to keep it clean
    sect = m.group()
    first_lines = '\n'.join(sect.split('\n')[:4])
    print(f"Section {m.start()}-{m.end()}:")
    print(first_lines)
    print("-" * 30)
