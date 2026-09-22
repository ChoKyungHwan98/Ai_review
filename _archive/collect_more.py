"""500건 분석을 위한 추가 수집.

목표: 최종 수집 ≈ 770건 (짧은 리뷰 35% 제외 후 분석 가능 ~500건)
현재: 400건 (추천 288 + 비추천 112)
추가: 추천 250 + 비추천 100 = 350건

추천/비추천 비율은 현재 72/28을 유지 (비추천 의도적 over-sampling 유지).
중복 ID는 자동 skip.
"""

import csv, time, httpx

APP_ID = 1623730
LANG = "koreana"
CSV_FILE = "reviews.csv"
URL = "https://store.steampowered.com/appreviews/{appid}"


def fetch(cursor: str, review_type: str) -> dict:
    params = {
        "json": 1, "filter": "recent", "language": LANG,
        "review_type": review_type, "purchase_type": "all",
        "num_per_page": 100, "cursor": cursor, "filter_offtopic_activity": 0,
    }
    r = httpx.get(URL.format(appid=APP_ID), params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def main():
    existing = []
    seen_ids = set()
    with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            existing.append(row)
            seen_ids.add(row["recommendationid"])
    pos_now = sum(1 for r in existing if r["voted_up"] == "1")
    neg_now = sum(1 for r in existing if r["voted_up"] == "0")
    print(f"현재: 총 {len(existing)}건 (추천 {pos_now} / 비추천 {neg_now})")

    targets = [("all", 250), ("negative", 100)]  # all에서 추천만 골라서 가져옴
    added = []

    for rtype, want in targets:
        cursor = "*"
        got = 0
        # all 모드일 땐 추천만 골라 담음
        while got < want:
            data = fetch(cursor, rtype)
            reviews = data.get("reviews", [])
            if not reviews: break
            for rv in reviews:
                rid = str(rv.get("recommendationid"))
                if rid in seen_ids: continue
                voted_up = 1 if rv.get("voted_up") else 0
                # all 모드에서는 추천만 추가 (negative는 별도 모드로 처리)
                if rtype == "all" and voted_up != 1: continue
                seen_ids.add(rid)
                author = rv.get("author", {})
                added.append({
                    "recommendationid": rid,
                    "content": rv.get("review", "").replace("\r"," ").replace("\n"," ").strip(),
                    "voted_up": str(voted_up),
                    "votes_up": rv.get("votes_up", 0),
                    "votes_funny": rv.get("votes_funny", 0),
                    "weighted_vote_score": rv.get("weighted_vote_score", "0"),
                    "playtime_at_review_min": author.get("playtime_at_review", 0),
                    "playtime_forever_min": author.get("playtime_forever", 0),
                    "author_steamid": author.get("steamid", ""),
                    "timestamp_created": rv.get("timestamp_created", 0),
                })
                got += 1
                if got >= want: break
            print(f"  [{rtype}] 추가 {got}/{want}")
            next_cursor = data.get("cursor")
            if not next_cursor or next_cursor == cursor: break
            cursor = next_cursor
            time.sleep(0.5)

    all_rows = existing + added
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    total_pos = sum(1 for r in all_rows if r["voted_up"] == "1")
    total_neg = sum(1 for r in all_rows if r["voted_up"] == "0")
    print(f"\n✅ {len(added)}건 추가 → 총 {len(all_rows)}건 (추천 {total_pos} / 비추천 {total_neg})")


if __name__ == "__main__":
    main()
