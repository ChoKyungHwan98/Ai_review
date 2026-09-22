"""전처리 + LLM 다차원 분석 (게임 기획자 모바일 이식 관점)

입력 : reviews.csv (수집된 한국어 스팀 팰월드 리뷰)
출력 : analysis.csv (감성, 카테고리, 핵심 포인트, 모바일 시사점)

분석 축:
1) sentiment      : 긍정 / 부정 / 중립
2) categories     : 게임플레이/그래픽/버그·최적화/멀티플레이/콘텐츠/UI·UX/가격/스토리/포켓몬유사성/창의성/기타 — 0~3개
3) main_points    : 핵심 문구 (각 ≤ 25자) 1~3개
4) mobile_impl    : 모바일적합 / 모바일부적합 / 모바일에서개선가능 / 무관
5) mobile_reason  : 한 줄 이유

이미 처리한 recommendationid는 skip → 중간에 멈춰도 이어서 재실행 가능.
"""

import os
import csv
import json
import time
import httpx
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")
URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"

IN_CSV  = "reviews.csv"
OUT_CSV = "analysis.csv"

# 너무 짧은 리뷰 제거 임계치
MIN_LEN = 8

SYSTEM = (
    "당신은 한국 모바일 게임사의 시장 분석가입니다. "
    "PC 스팀 게임 '팰월드(Palworld)' 한국 유저 리뷰를 분석하여 "
    "모바일 이식판의 기획 의사결정을 돕는 인사이트를 제공합니다."
)

USER_TEMPLATE = """다음은 한국 스팀 유저가 작성한 팰월드 리뷰입니다.
voted_up = {voted_up} (1=추천, 0=비추천), 플레이타임 = {playtime_h}시간

리뷰: "{content}"

아래 JSON 한 덩어리만 출력해주세요 (코드블록·설명 금지):
{{
  "sentiment": "긍정" 또는 "부정" 또는 "중립",
  "categories": [택1~3, 가능 값: "게임플레이","그래픽","버그·최적화","멀티플레이","콘텐츠분량","UI·UX","가격","스토리","포켓몬유사성","창의성","기타"],
  "main_points": [핵심 포인트 1~3개, 각 25자 이내],
  "mobile_impl": "모바일적합" 또는 "모바일부적합" 또는 "모바일에서개선가능" 또는 "무관",
  "mobile_reason": "한 줄 사유 (40자 이내)"
}}"""


def call_llm(content: str, voted_up: int, playtime_h: float, retries: int = 1) -> dict:
    user = USER_TEMPLATE.format(content=content[:1200], voted_up=voted_up, playtime_h=f"{playtime_h:.1f}")
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = httpx.post(URL, headers=headers, json=body, timeout=45.0)
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            # 혹시 모를 코드블록 제거
            if "```" in txt:
                txt = txt.split("```")[1]
                if txt.startswith("json"):
                    txt = txt[4:]
            return json.loads(txt.strip())
        except Exception as e:
            last_err = e
            time.sleep(1.5)
    raise last_err


def main():
    if not API_KEY or "여기에" in API_KEY:
        raise SystemExit("❌ .env의 OPENROUTER_API_KEY를 확인하세요.")

    # 입력 로드
    rows = []
    with open(IN_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            content = (row.get("content") or "").strip()
            if len(content) < MIN_LEN:
                continue
            rows.append(row)
    print(f"분석 대상 {len(rows)}건 (짧은 리뷰 제외 후)")

    # 기존 결과 로드 (재개)
    done_ids = set()
    if os.path.exists(OUT_CSV):
        with open(OUT_CSV, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                done_ids.add(r["recommendationid"])
        print(f"이미 분석된 {len(done_ids)}건은 skip")

    fieldnames = [
        "recommendationid", "voted_up", "playtime_h", "content",
        "sentiment", "categories", "main_points", "mobile_impl", "mobile_reason"
    ]
    write_header = not os.path.exists(OUT_CSV)
    f_out = open(OUT_CSV, "a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    if write_header:
        writer.writeheader()

    n_ok = n_fail = 0
    for i, row in enumerate(rows, 1):
        rid = row["recommendationid"]
        if rid in done_ids:
            continue
        voted = int(row["voted_up"])
        playtime_h = int(row["playtime_forever_min"] or 0) / 60.0
        try:
            res = call_llm(row["content"], voted, playtime_h)
            writer.writerow({
                "recommendationid": rid,
                "voted_up": voted,
                "playtime_h": f"{playtime_h:.1f}",
                "content": row["content"][:500],
                "sentiment": res.get("sentiment", ""),
                "categories": "|".join(res.get("categories", [])),
                "main_points": "|".join(res.get("main_points", [])),
                "mobile_impl": res.get("mobile_impl", ""),
                "mobile_reason": res.get("mobile_reason", ""),
            })
            f_out.flush()
            n_ok += 1
        except Exception as e:
            n_fail += 1
            print(f"  [{i}/{len(rows)}] FAIL rid={rid}: {e}")
            continue
        if i % 20 == 0:
            print(f"  진행 {i}/{len(rows)}  ok={n_ok} fail={n_fail}")

    f_out.close()
    print(f"\n✅ 완료: {n_ok}건 분석 / {n_fail}건 실패 → {OUT_CSV}")


if __name__ == "__main__":
    main()
