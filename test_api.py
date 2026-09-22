"""API 자동 테스트 스크립트

실행 전 별도 터미널에서: uvicorn main:app --host 127.0.0.1 --port 8765
실행: python test_api.py
"""

import httpx

BASE_URL = "http://127.0.0.1:8765"


def test_api():
    print("=== API 테스트 시작 ===")

    # 1. 헬스체크
    print("\n[1] GET / - 헬스체크")
    r = httpx.get(f"{BASE_URL}/")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")

    # 2. 리뷰 추가
    print("\n[2] POST /reviews - 리뷰 추가")
    r = httpx.post(f"{BASE_URL}/reviews", json={
        "content": "정말 재밌는 게임이에요! 추천합니다.",
        "game_name": "팰월드"
    })
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")
    review_id = r.json()["id"]

    # 3. 리뷰 목록
    print("\n[3] GET /reviews - 리뷰 목록")
    r = httpx.get(f"{BASE_URL}/reviews")
    print(f"  Status: {r.status_code}")
    print(f"  리뷰 수: {len(r.json())}")

    # 4. 분석 실행 (API 키 미설정 시 500 가능)
    print("\n[4] POST /analyze - 분석 실행")
    try:
        r = httpx.post(f"{BASE_URL}/analyze", json={"review_id": review_id}, timeout=30.0)
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.json()}")
    except Exception as e:
        print(f"  (분석은 OPENROUTER_API_KEY 설정 후 동작합니다) - {e}")

    # 5. 통계
    print("\n[5] GET /stats - 통계")
    r = httpx.get(f"{BASE_URL}/stats")
    print(f"  Status: {r.status_code}")
    print(f"  Response: {r.json()}")

    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    test_api()
