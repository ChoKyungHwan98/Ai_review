FILE = r'c:\Users\Admin\Desktop\게임기획\포트폴리오\ai-reviews\verify_analysis.py'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace with config import and dynamic values
old_vars = """ANALYSIS_CSV  = "analysis_v2.csv"
VERIFY_SET    = "verify_set.csv"     # 선정된 30건 + LLM 재분석 결과
VERIFY_REPORT = "verify_report.json" # 대시보드용"""

new_vars = """from config import cfg

def get_analysis_csv(): return cfg.ANALYSIS_CSV
def get_verify_set_csv(): 
    import os
    p = os.path.join(cfg.BASE_DIR, "data", str(cfg.APP_ID))
    os.makedirs(p, exist_ok=True)
    return os.path.join(p, "verify_set.csv")
def get_verify_report_json(): return cfg.VERIFY_JSON"""

content = content.replace(old_vars, new_vars)

# Replace references with dynamic getters
content = content.replace("ANALYSIS_CSV", "get_analysis_csv()")
content = content.replace("VERIFY_SET", "get_verify_set_csv()")
content = content.replace("VERIFY_REPORT", "get_verify_report_json()")

# Replace API KEY, URL, MODEL to use cfg
content = content.replace('API_KEY = os.getenv("OPENROUTER_API_KEY")', 'API_KEY = cfg.OPENROUTER_API_KEY')
content = content.replace('URL = "https://openrouter.ai/api/v1/chat/completions"', 'URL = cfg.OPENROUTER_URL')
content = content.replace('MODEL = "google/gemini-2.0-flash-001"', 'MODEL = cfg.MODEL')

# Replace the text "팰월드" inside verify prompt to be dynamic
content = content.replace("팰월드 리뷰의 실제 감성", "리뷰의 실제 감성")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: verify_analysis.py updated to use cfg!")
