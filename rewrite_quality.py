FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\quality_check.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace with config import and dynamic values
old_vars = 'REVIEWS_CSV = "reviews.csv"\nANALYSIS_CSV = "analysis_v2.csv"\nPOPULATION_POS_RATE = 0.9507  # Steam 공식 한국어 모집단 추천 비율 (build_insights_v4 결과)'

new_vars = """from config import cfg

def get_reviews_csv(): return cfg.REVIEWS_CSV
def get_analysis_csv(): return cfg.ANALYSIS_CSV

# Fetch positive rate from population stats dynamically
def get_pop_pos_rate():
    try:
        from main import review_population_stats
        stats = review_population_stats(cfg.APP_ID)
        return stats["korean"]["positive"] / stats["korean"]["total"] if stats["korean"]["total"] > 0 else 0.95
    except Exception:
        return 0.95
"""

content = content.replace(old_vars, new_vars)

# Replace references of REVIEWS_CSV and ANALYSIS_CSV with getters
content = content.replace("REVIEWS_CSV", "get_reviews_csv()")
content = content.replace("ANALYSIS_CSV", "get_analysis_csv()")
content = content.replace("POPULATION_POS_RATE", "get_pop_pos_rate()")
content = content.replace("quality_report.json", "cfg.QUALITY_JSON")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: quality_check.py updated to use cfg!")
