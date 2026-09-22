"""LLM 분석 함수 - OpenRouter API 사용"""

import os
import json
import httpx
from config import cfg

# OpenRouter API 설정
OPENROUTER_API_KEY = cfg.OPENROUTER_API_KEY
OPENROUTER_URL = cfg.OPENROUTER_URL
MODEL = cfg.MODEL


def analyze_review(content: str) -> dict:
    """리뷰 텍스트를 분석해서 감성, 키워드, 확신도를 반환합니다.

    Raises:
        ValueError: API 키 미설정
        RuntimeError: LLM 호출 또는 응답 파싱 실패
    """

    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY.startswith("sk-or-v1-여기에"):
        raise ValueError("OPENROUTER_API_KEY가 설정되지 않았습니다! .env 파일을 확인하세요.")

    prompt = f'''
다음 게임 리뷰를 분석해주세요.

리뷰: "{content}"

아래 JSON 형식으로만 응답해주세요:
{{
    "sentiment": "긍정" 또는 "부정" 또는 "중립",
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "confidence": 0.0에서 1.0 사이의 확신도
}}
'''

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        response = httpx.post(OPENROUTER_URL, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        analysis = json.loads(content.strip())
        return {
            "sentiment": analysis.get("sentiment", "중립"),
            "keywords": analysis.get("keywords", []),
            "confidence": float(analysis.get("confidence", 0.5))
        }
    except Exception as e:
        print(f"분석 에러: {e}")
        raise RuntimeError(f"LLM 분석 실패: {e}") from e
