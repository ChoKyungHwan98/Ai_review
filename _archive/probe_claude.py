"""Claude 3.5 Sonnet 모델 1건 호출 검증."""
import os, json, re, httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemini-2.0-flash-001"

sample = "전작들보다 훨씬 발전했고 친구랑 같이 하면 시간 가는 줄 모름. 다만 후반에 버그가 좀 있긴 함. 그래도 가격 대비 만족."

body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "JSON으로만 답변. 코드블록 금지."},
        {"role": "user", "content": f"리뷰: {sample}\n\n다음 JSON 출력:\n{{\"sentiment\":\"POSITIVE|NEGATIVE|MIXED\",\"keywords\":[\"w1\",\"w2\"]}}"}
    ],
    "temperature": 0.2,
    "max_tokens": 200,
}
r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
               headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
               json=body, timeout=60.0)
print("Status:", r.status_code)
if r.status_code != 200:
    print("Body:", r.text[:500])
else:
    j = r.json()
    print("Model used:", j.get("model"))
    usage = j.get("usage", {})
    print("Tokens:", usage)
    out = j["choices"][0]["message"]["content"]
    print("Response:")
    print(out)
