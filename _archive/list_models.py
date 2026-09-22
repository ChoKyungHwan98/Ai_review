"""OpenRouter에서 사용 가능한 모델 목록 + 가격 확인."""
import os, httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

r = httpx.get("https://openrouter.ai/api/v1/models",
              headers={"Authorization": f"Bearer {API_KEY}"},
              timeout=30.0)
r.raise_for_status()
models = r.json()["data"]

# 관심 키워드
keywords = ["claude", "gpt-4o", "gemini-2", "deepseek-v3", "deepseek-chat", "qwen"]
print(f"총 {len(models)}개 모델 — 분석에 적합한 것만 필터링\n")

picks = []
for m in models:
    mid = m["id"].lower()
    if not any(k in mid for k in keywords):
        continue
    pricing = m.get("pricing", {})
    try:
        p_in = float(pricing.get("prompt", "0")) * 1_000_000
        p_out = float(pricing.get("completion", "0")) * 1_000_000
    except Exception:
        p_in = p_out = 0
    # 무료/실험판 제외
    if ":free" in mid or p_in == 0 and "free" in mid:
        continue
    picks.append((m["id"], p_in, p_out, m.get("context_length", 0)))

# 가격으로 정렬
picks.sort(key=lambda x: (x[1] + x[2]))

print(f"{'MODEL':<55} {'IN/1M':>8} {'OUT/1M':>8} {'CTX':>10}")
print("-" * 85)
for mid, pi, po, ctx in picks:
    print(f"{mid:<55} ${pi:>6.2f}  ${po:>6.2f}  {ctx:>10}")
