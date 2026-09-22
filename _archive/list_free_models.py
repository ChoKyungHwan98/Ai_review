"""OpenRouter :free 모델 중 한국어/일반 분석에 적합한 것 골라내기."""
import os, httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

r = httpx.get("https://openrouter.ai/api/v1/models",
              headers={"Authorization": f"Bearer {API_KEY}"},
              timeout=30.0)
r.raise_for_status()
models = r.json()["data"]

# :free 만, 코딩 전용/비전 모델 제외
prefer = ["gemini", "deepseek-chat", "llama", "mistral-small", "qwen", "glm"]
exclude = ["coder", "code", "vision", "image", "embed", "vl-"]

frees = []
for m in models:
    mid = m["id"].lower()
    if not mid.endswith(":free"):
        continue
    if any(e in mid for e in exclude):
        continue
    if not any(p in mid for p in prefer):
        continue
    frees.append((m["id"], m.get("context_length", 0)))

print(f"=== 분석에 쓸만한 :free 모델 ({len(frees)}개) ===\n")
print(f"{'MODEL':<60} {'CTX':>10}")
print("-" * 75)
for mid, ctx in sorted(frees):
    print(f"{mid:<60} {ctx:>10}")
