import sys

FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\analyze_reviews_v2.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace settings block to use config.cfg dynamically
old_settings = """API_KEY = os.getenv("OPENROUTER_API_KEY")
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemini-2.0-flash-001"   # 초저렴 유료 ($0.10/$0.40 per 1M tokens) — 254건 약 $0.06

IN_CSV  = "reviews.csv"
OUT_CSV = "analysis_v2.csv"
MIN_LEN = 8"""

new_settings = """from config import cfg

API_KEY = cfg.OPENROUTER_API_KEY
URL = cfg.OPENROUTER_URL
MODEL = cfg.MODEL

def get_in_csv(): return cfg.REVIEWS_CSV
def get_out_csv(): return cfg.ANALYSIS_CSV
def get_min_len(): return cfg.MIN_REVIEW_LEN"""

content = content.replace(old_settings, new_settings)

# Let's replace IN_CSV and OUT_CSV and MIN_LEN occurrences in functions
content = content.replace("IN_CSV", "get_in_csv()")
content = content.replace("OUT_CSV", "get_out_csv()")
content = content.replace("MIN_LEN", "get_min_len()")

# Make the prompt dynamic based on the game name
old_system = """SYSTEM = (
    "당신은 한국 모바일 게임사의 시니어 시장 분석가입니다. "
    "PC 스팀 게임 '팰월드(Palworld)' 한국 유저 리뷰를 깊이 있게 분석하여, "
    "모바일 이식판의 기획·QA·운영 의사결정을 돕는 데이터 인사이트를 제공합니다. "
    "단순 감성을 넘어 (1) ABSA 6-Aspect (2) 구체적 감정 (3) 토픽 분류된 키워드 "
    "(4) 모바일 이식 시사점까지 한 번에 추출합니다."
)"""

new_system = """SYSTEM = (
    "당신은 한국 모바일 게임사의 시니어 시장 분석가입니다. "
    f"PC 스팀 게임 '{cfg.get_game_name()}' 한국 유저 리뷰를 깊이 있게 분석하여, "
    "모바일 이식판의 기획·QA·운영 의사결정을 돕는 데이터 인사이트를 제공합니다. "
    "단순 감성을 넘어 (1) ABSA 6-Aspect (2) 구체적 감정 (3) 토픽 분류된 키워드 "
    "(4) 모바일 이식 시사점까지 한 번에 추출합니다."
)"""

content = content.replace(old_system, new_system)

# Let's also do user template game name
content = content.replace("팰월드 리뷰입니다.", "리뷰입니다.")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Modified analyze_reviews_v2.py successfully!")
