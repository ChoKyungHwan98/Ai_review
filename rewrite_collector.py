import re

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\collect_reviews_v2.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace settings block to use config.cfg dynamically
old_settings = """# ─── 설정 ──────────────────────────────────────────────────────────────
APP_ID = 1623730          # Palworld
LANG = "koreana"          # 한국어만
TARGET_ERROR_PCT = 3      # 목표 오차한계 ±3%
MIN_NEG = 100             # 부정 리뷰 최소 확보 목표
Z_95 = 1.96               # 95% 신뢰수준
OUT_CSV = "reviews_v2.csv"
OUT_JSON = "sample_design_v2.json"
URL = "https://store.steampowered.com/appreviews/{appid}"
"""

new_settings = """from config import cfg

# ─── 설정 ──────────────────────────────────────────────────────────────
def get_app_id(): return cfg.APP_ID
def get_lang(): return cfg.LANG
def get_target_error(): return cfg.TARGET_ERROR_PCT
def get_min_neg(): return cfg.MIN_NEG_REVIEWS
def get_z95(): return cfg.Z_95
def get_out_csv(): return cfg.REVIEWS_CSV
def get_out_json(): return cfg.SAMPLE_JSON
def get_url(): return cfg.STEAM_API_URL
"""

# Let's replace the occurrences of global variables inside functions
content = content.replace(old_settings, new_settings)

# Replace fetch_population function body variables
content = content.replace('URL.format(appid=APP_ID)', 'get_url().format(appid=get_app_id())')
content = content.replace('"language": LANG,', '"language": get_lang(),')

# Replace decide_sample_size e definition
content = content.replace('e = TARGET_ERROR_PCT / 100', 'e = get_target_error() / 100')
content = content.replace('p=0.5, z=Z_95, e=e', 'p=0.5, z=get_z95(), e=e')
content = content.replace('p=0.5, z=Z_95', 'p=0.5, z=get_z95()')
content = content.replace('MIN_NEG / neg_rate', 'get_min_neg() / neg_rate')

# Replace collect_reviews body variables
content = content.replace('URL.format(appid=APP_ID)', 'get_url().format(appid=get_app_id())')
content = content.replace('"language": LANG,', '"language": get_lang(),')

# Replace main body variables
content = content.replace("print(f\"  목표: 오차 ±{TARGET_ERROR_PCT}% + 부정 최소 {MIN_NEG}건\")", "print(f\"  목표: 오차 ±{get_target_error()}% + 부정 최소 {get_min_neg()}건\")")
content = content.replace("OUT_CSV", "get_out_csv()")
content = content.replace("OUT_JSON", "get_out_json()")

# Let's write the modified content back
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Modified collect_reviews_v2.py successfully!")
