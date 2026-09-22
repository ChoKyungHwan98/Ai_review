"""v2 LLM 다차원 분석 (강의 표준 패턴 + 모바일 면접 관점)

업그레이드 사항 (토큰 최적화 및 비동기 처리 적용):
1. 프롬프트 패킹(Prompt Packing): 리뷰 N건을 배열로 묶어 한 번에 분석 (시스템 프롬프트 비용 절감)
2. 비동기(Async) 병렬 처리: asyncio 및 httpx.AsyncClient를 이용한 다중 배치 동시 전송
3. 모델: Anthropic Claude 3.5 Sonnet 등 (설정에 따름)
4. Fallback 로직: 배치 처리 실패 시 1건씩 개별 재처리하여 데이터 유실 방지
"""

import os
import sys
import csv
import json
import time
import re
import asyncio
import httpx
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
from config import cfg

API_KEY = cfg.OPENROUTER_API_KEY
URL = cfg.OPENROUTER_URL
MODEL = cfg.MODEL

def get_in_csv(): return cfg.REVIEWS_CSV
def get_out_csv(): return cfg.ANALYSIS_CSV
def get_min_len(): return cfg.MIN_REVIEW_LEN

ASPECTS = ["graphics", "gameplay", "story", "performance", "value"]
BATCH_SIZE = 5  # 한 번의 LLM 호출에 담을 리뷰 수
CONCURRENCY_LIMIT = 3  # 동시에 보낼 배치 요청 수

SYSTEM = (
    "당신은 게임 유저 데이터 분석 전문가입니다. "
    "Steam 한국 유저 리뷰를 분석하여 "
    "유저 반응의 강점과 약점을 객관적으로 파악하는 인사이트를 제공합니다. "
    "주어진 리뷰 배열을 분석하여, 각 리뷰의 ID와 분석 결과를 포함한 JSON 배열(Array)만 출력하세요. "
    "코드블록이나 부가 설명은 절대 금지합니다."
)

USER_TEMPLATE = """다음은 한국 스팀 유저가 작성한 리뷰 배열입니다.
{reviews_json}

반드시 아래 형식의 JSON 배열(Array) 하나만 출력하세요.
[
  {{
    "recommendationid": "리뷰 고유 ID (입력받은 ID 그대로)",
    "overall_sentiment": "POSITIVE|NEGATIVE|MIXED|NEUTRAL",
    "emotion": "JOY|ANGER|DISAPPOINTMENT|SURPRISE|BOREDOM|SATISFACTION|NEUTRAL",
    "aspects": {{
      "graphics": {{"sentiment": "POSITIVE|NEGATIVE|NONE", "evidence": "축약된 근거"}},
      "gameplay": {{"sentiment": "...", "evidence": "..."}},
      "story": {{"sentiment": "...", "evidence": "..."}},
      "performance": {{"sentiment": "...", "evidence": "..."}},
      "value": {{"sentiment": "...", "evidence": "..."}}
    }},
    "key_phrase": "유저 입장 요약(25자 내외)",
    "keywords": [
      {{"word": "키워드", "topic": "technical|content|value|community|other"}}
    ],
    "confidence": 0.85
  }}
]

규칙:
- 언급되지 않은 aspect는 sentiment="NONE", evidence=""
- evidence는 30자 이내 축약
- keywords는 최대 3개
"""

def clean_json_response(text: str) -> str:
    text = text.strip()
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if m: return m.group(1).strip()
    m = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if m: return m.group(1).strip()
    m = re.search(r"(\[[\s\S]*\])", text)
    if m: return m.group(1).strip()
    return text

async def call_llm_async(client: httpx.AsyncClient, reviews: list, retries: int = 1) -> list:
    reviews_data = []
    for r in reviews:
        reviews_data.append({
            "id": r["recommendationid"],
            "voted_up": r["voted_up"],
            "playtime_h": f"{int(r['playtime_forever_min'] or 0)/60.0:.1f}",
            "content": r["content"][:1000]
        })
    
    user_prompt = USER_TEMPLATE.format(reviews_json=json.dumps(reviews_data, ensure_ascii=False, indent=2))
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user_prompt}],
        "temperature": 0.2,
        "max_tokens": 500 * len(reviews),  # 리뷰당 ~350토큰이면 충분 (기존 1200에서 축소)
    }
    
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = await client.post(URL, headers=headers, json=body, timeout=120.0)
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            parsed = json.loads(clean_json_response(txt))
            if not isinstance(parsed, list):
                raise ValueError("LLM응답이 배열(List) 형태가 아닙니다.")
            return parsed
        except Exception as e:
            last_err = e
            await asyncio.sleep(2.0)
            
    raise last_err

def flatten(original_row, res):
    rid = original_row["recommendationid"]
    voted = int(original_row["voted_up"])
    playtime_h = int(original_row["playtime_forever_min"] or 0) / 60.0
    content = original_row["content"]
    
    conf = float(res.get("confidence", 0.85))
    needs_ver = "true" if conf < 0.75 else "false"
    
    row = {
        "recommendationid": rid,
        "voted_up": voted,
        "playtime_h": f"{playtime_h:.1f}",
        "content": content[:500],
        "overall_sentiment": res.get("overall_sentiment", ""),
        "emotion": res.get("emotion", ""),
        "key_phrase": res.get("key_phrase", ""),
        "confidence": f"{conf:.2f}",
        "needs_verification": needs_ver,
    }
    
    aspects = res.get("aspects", {}) or {}
    for a in ASPECTS:
        d = aspects.get(a, {}) or {}
        sentiment = d.get("sentiment", "NONE")
        if sentiment == "NOT_MENTIONED": sentiment = "NONE"
        row[f"aspect_{a}_sentiment"] = sentiment
        row[f"aspect_{a}_evidence"]  = (d.get("evidence", "") or "")[:120]
        
    kws = res.get("keywords", []) or []
    row["keywords"] = "|".join(f"{k.get('word','')}@{k.get('topic','other')}" for k in kws if k.get("word"))
    return row

FIELDNAMES = (
    ["recommendationid", "voted_up", "playtime_h", "content",
     "overall_sentiment", "emotion", "key_phrase", "confidence", "needs_verification"]
    + [f"aspect_{a}_sentiment" for a in ASPECTS]
    + [f"aspect_{a}_evidence"  for a in ASPECTS]
    + ["keywords"]
)

async def process_batch(client, batch, semaphore, writer, f_out, stats):
    async with semaphore:
        try:
            results = await call_llm_async(client, batch)
            res_dict = {str(r.get("recommendationid")): r for r in results if r.get("recommendationid")}
            
            for orig_row in batch:
                rid = orig_row["recommendationid"]
                res = res_dict.get(rid)
                if res:
                    writer.writerow(flatten(orig_row, res))
                    stats["ok"] += 1
                else:
                    raise ValueError(f"ID {rid} 누락됨")
            f_out.flush()
        except Exception as e:
            print(f"  [배치 실패, 개별 재시도] {str(e)[:80]}")
            for orig_row in batch:
                try:
                    single_res = await call_llm_async(client, [orig_row])
                    if single_res and len(single_res) > 0:
                        writer.writerow(flatten(orig_row, single_res[0]))
                        f_out.flush()
                        stats["ok"] += 1
                    else:
                        raise ValueError("빈 응답")
                except Exception as e2:
                    stats["fail"] += 1
                    print(f"  [개별 실패] rid={orig_row['recommendationid']}: {str(e2)[:80]}")

async def run_pipeline():
    if not API_KEY or "여기에" in API_KEY:
        raise SystemExit("❌ .env의 OPENROUTER_API_KEY를 확인하세요.")

    rows = []
    with open(get_in_csv(), "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            content = (row.get("content") or "").strip()
            if len(content) < get_min_len(): continue
            rows.append(row)
            
    print(f"분석 대상 {len(rows)}건 (짧은 리뷰 제외 후)")
    print(f"모델: {MODEL}")

    done_ids = set()
    if os.path.exists(get_out_csv()):
        with open(get_out_csv(), "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                done_ids.add(r["recommendationid"])
        print(f"이미 분석된 {len(done_ids)}건은 skip (재개)")

    pending_rows = [r for r in rows if r["recommendationid"] not in done_ids]
    
    if not pending_rows:
        print("\n✅ 더 이상 분석할 리뷰가 없습니다.")
        return

    write_header = not os.path.exists(get_out_csv())
    f_out = open(get_out_csv(), "a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(f_out, fieldnames=FIELDNAMES)
    if write_header: writer.writeheader()

    stats = {"ok": 0, "fail": 0}
    
    batches = [pending_rows[i:i + BATCH_SIZE] for i in range(0, len(pending_rows), BATCH_SIZE)]
    print(f"총 {len(batches)}개 배치(단위: {BATCH_SIZE}건) 실행 준비 중...")
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=10)) as client:
        tasks = []
        for b in batches:
            tasks.append(asyncio.create_task(process_batch(client, b, semaphore, writer, f_out, stats)))
        
        for i, t in enumerate(asyncio.as_completed(tasks), 1):
            await t
            if i % max(1, (len(batches)//10)) == 0 or i == len(batches):
                print(f"  진행 {i}/{len(batches)} 배치 처리 완료 (누적 ok={stats['ok']} fail={stats['fail']})")

    f_out.close()
    print(f"\n✅ 완료: {stats['ok']}건 분석 / {stats['fail']}건 실패 → {get_out_csv()}")

def main():
    asyncio.run(run_pipeline())

if __name__ == "__main__":
    main()
