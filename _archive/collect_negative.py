"""비추천(부정) 한국어 리뷰만 추가 수집해서 reviews.csv에 병합.

분석 깊이를 위해 부정 표본을 보강. 기존 reviews.csv를 읽고,
중복 없이 비추천 리뷰를 100건까지 추가한다.
"""

import csv
import time
import httpx

APP_ID = 1623730
TARGET_NEG = 100
LANG = "koreana"
CSV_FILE = "reviews.csv"
URL = "https://store.steampowered.com/appreviews/{appid}"


def fetch(cursor: str) -> dict:
    params = {
        "json": 1,
        "filter": "recent",
        "language": LANG,
        "review_type": "negative",   # 비추천만
        "purchase_type": "all",
        "num_per_page": 100,
        "cursor": cursor,
        "filter_offtopic_activity": 0,
    }
    r = httpx.get(URL.format(appid=APP_ID), params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def main():
    # 기존 CSV 로드 (중복 방지)
    existing = []
    seen_ids = set()
    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing.append(row)
            seen_ids.add(row["recommendationid"])
    print(f"기존 {len(existing)}건 로드 (중 비추천 {sum(1 for r in existing if r['voted_up']=='0')}건)")

    added = []
    cursor = "*"
    while len(added) < TARGET_NEG:
        data = fetch(cursor)
        reviews = data.get("reviews", [])
        if not reviews:
            break
        for rv in reviews:
            rid = str(rv.get("recommendationid"))
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            author = rv.get("author", {})
            added.append({
                "recommendationid": rid,
                "content": rv.get("review", "").replace("\r", " ").replace("\n", " ").strip(),
                "voted_up": "0",
                "votes_up": rv.get("votes_up", 0),
                "votes_funny": rv.get("votes_funny", 0),
                "weighted_vote_score": rv.get("weighted_vote_score", "0"),
                "playtime_at_review_min": author.get("playtime_at_review", 0),
                "playtime_forever_min": author.get("playtime_forever", 0),
                "author_steamid": author.get("steamid", ""),
                "timestamp_created": rv.get("timestamp_created", 0),
            })
            if len(added) >= TARGET_NEG:
                break
        print(f"  비추천 추가 {len(added)}/{TARGET_NEG}")
        next_cursor = data.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        time.sleep(0.6)

    # 병합 저장
    all_rows = existing + added
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    total_pos = sum(1 for r in all_rows if r["voted_up"] == "1")
    total_neg = sum(1 for r in all_rows if r["voted_up"] == "0")
    print(f"\n✅ 비추천 {len(added)}건 추가 → 총 {len(all_rows)}건 (추천 {total_pos} / 비추천 {total_neg})")


if __name__ == "__main__":
    main()
