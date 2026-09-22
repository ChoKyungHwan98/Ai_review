import httpx, json

app_id = 1627720
url = (
    f"https://store.steampowered.com/appreviews/{app_id}"
    f"?json=1&filter=helpful&language=koreana&purchase_type=all"
    f"&num_per_page=20&review_type=all"
)
print(f"Fetching: {url}\n")

r = httpx.get(url, timeout=15.0)
print(f"Status: {r.status_code}")
data = r.json()

reviews = data.get("reviews", [])
print(f"Reviews returned: {len(reviews)}")
print()

with open("helpful_api_test.txt", "w", encoding="utf-8") as out:
    out.write(f"Status: {r.status_code}\n")
    out.write(f"Reviews: {len(reviews)}\n\n")
    for i, rev in enumerate(reviews[:5]):
        out.write(f"[{i+1}] voted_up={rev.get('voted_up')} | votes_up={rev.get('votes_up')} | ws={rev.get('weighted_vote_score')}\n")
        content = rev.get("review", "")[:150].replace('\n', ' ')
        out.write(f"    {content}\n\n")

print("Done. See helpful_api_test.txt")
