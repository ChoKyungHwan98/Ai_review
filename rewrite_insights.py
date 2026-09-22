FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\build_insights_v4.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace variables block in build_insights_v4.py
old_vars = 'os.makedirs("charts_v4", exist_ok=True)\n\nAPP_ID = 1623730'

new_vars = """from config import cfg

APP_ID = cfg.APP_ID
def get_charts_dir(): return cfg.CHARTS_DIR
os.makedirs(get_charts_dir(), exist_ok=True)"""

content = content.replace(old_vars, new_vars)

# Replace all other occurrences of hardcoded filenames
content = content.replace('"reviews.csv"', 'cfg.REVIEWS_CSV')
content = content.replace('"analysis_v2.csv"', 'cfg.ANALYSIS_CSV')
content = content.replace('"insights_v4.json"', 'cfg.INSIGHTS_JSON')
content = content.replace('"quality_report.json"', 'cfg.QUALITY_JSON')
content = content.replace('"verify_report.json"', 'cfg.VERIFY_JSON')
content = content.replace('"sample_design.json"', 'cfg.SAMPLE_JSON')

# Replace hardcoded APP_ID in store request with dynamic APP_ID
content = content.replace('f"https://store.steampowered.com/appreviews/1623730"', 'f"https://store.steampowered.com/appreviews/{cfg.APP_ID}"')
content = content.replace('params={"json": 1, "filter": "recent", "language": "koreana"', 'params={"json": 1, "filter": "recent", "language": cfg.LANG')

# Replace saving charts to be inside cfg.CHARTS_DIR
content = content.replace('os.path.join("charts_v4",', 'os.path.join(cfg.CHARTS_DIR,')
content = content.replace('plt.savefig(f"charts_v4/', 'plt.savefig(os.path.join(cfg.CHARTS_DIR, ')
content = content.replace('plt.savefig("charts_v4/', 'plt.savefig(os.path.join(cfg.CHARTS_DIR, ')

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: build_insights_v4.py updated to use cfg!")
