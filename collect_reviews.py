"""Steam 팰월드(Palworld, AppID 1623730) 한국어 리뷰 수집

Steam Storefront의 공개 appreviews API를 사용 (API 키 불필요).
- filter=recent: 최신순
- language=koreana: 한국어
- num_per_page=100 (최대), cursor로 페이지네이션

산출물: reviews.csv
컬럼: recommendationid, content, voted_up, votes_up, votes_funny,
      weighted_vote_score, playtime_at_review_min, playtime_forever_min,
      author_steamid, timestamp_created
"""

import csv
import time
import json
import httpx
from config import cfg

APP_ID = cfg.APP_ID
TARGET = 300       # 목표 수집 건수
LANG = cfg.LANG
OUT_CSV = cfg.REVIEWS_CSV

URL = "https://store.steampowered.com/appreviews/{appid}"


def fetch_page(cursor: str = "*") -> dict:
    params = {
        "json": 1,
        "filter": "recent",
        "language": LANG,
        "review_type": "all",
        "purchase_type": "all",
        "num_per_page": 100,
        "cursor": cursor,
        "filter_offtopic_activity": 0,
    }
    r = httpx.get(URL.format(appid=APP_ID), params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def main():
    collected = []
    seen_ids = set()
    cursor = "*"

    while len(collected) < TARGET:
        data = fetch_page(cursor)
        reviews = data.get("reviews", [])
        if not reviews:
            print("⚠️ 더 이상 리뷰가 없습니다. 종료.")
            break

        new_count = 0
        for rv in reviews:
            rid = rv.get("recommendationid")
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            author = rv.get("author", {})
            collected.append({
                "recommendationid": rid,
                "content": rv.get("review", "").replace("\r", " ").replace("\n", " ").strip(),
                "voted_up": int(rv.get("voted_up", False)),
                "votes_up": rv.get("votes_up", 0),
                "votes_funny": rv.get("votes_funny", 0),
                "weighted_vote_score": rv.get("weighted_vote_score", "0"),
                "playtime_at_review_min": author.get("playtime_at_review", 0),
                "playtime_forever_min": author.get("playtime_forever", 0),
                "author_steamid": author.get("steamid", ""),
                "timestamp_created": rv.get("timestamp_created", 0),
            })
            new_count += 1
            if len(collected) >= TARGET:
                break

        print(f"  수집 {len(collected)}/{TARGET} (이번 페이지 신규 {new_count}건)")

        next_cursor = data.get("cursor")
        if not next_cursor or next_cursor == cursor:
            print("⚠️ 페이지네이션 종료 신호.")
            break
        cursor = next_cursor
        time.sleep(0.6)  # 매너 딜레이

    # CSV 저장
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(collected[0].keys()))
        writer.writeheader()
        writer.writerows(collected)

    # 요약
    pos = sum(1 for c in collected if c["voted_up"] == 1)
    neg = len(collected) - pos
    avg_play = sum(c["playtime_forever_min"] for c in collected) / max(len(collected), 1) / 60
    print(f"\n✅ 총 {len(collected)}건 수집 → {OUT_CSV}")
    print(f"   추천: {pos} ({pos/len(collected)*100:.1f}%)  비추천: {neg} ({neg/len(collected)*100:.1f}%)")
    print(f"   평균 플레이타임: {avg_play:.1f}시간")


if __name__ == "__main__":
    main()
