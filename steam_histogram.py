"""Steam이 게임마다 주는 날짜별 추천 · 비추천 수를 가져와 정리한다.

우리가 수집한 표본이 아니라 Steam에 올라온 전체 리뷰(모든 언어)를 센 숫자다.
AI를 부르지 않고, 받은 결과는 프로젝트 폴더에 저장해 두었다가 '최신화'를 누를 때만 다시 받는다.
"""

import json
import os
from datetime import datetime, timezone

URL = "https://store.steampowered.com/appreviewhistogram/{app_id}"
NEWS_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
FILENAME = "review_histogram.json"


def parse(payload, now=None):
    """Steam 응답을 {fetched_at, rollup_type, rollups, recent}로 바꾼다. 날짜는 UTC 기준 YYYY-MM-DD."""
    results = (payload or {}).get("results") or {}

    def rows(key):
        out = []
        for row in results.get(key) or []:
            day = datetime.fromtimestamp(int(row["date"]), timezone.utc).strftime("%Y-%m-%d")
            out.append({
                "date": day,
                "up": int(row.get("recommendations_up") or 0),
                "down": int(row.get("recommendations_down") or 0),
            })
        return out

    return {
        "fetched_at": (now or datetime.now()).strftime("%Y-%m-%d %H:%M"),
        "rollup_type": results.get("rollup_type") or "month",   # 전체 기간을 묶은 단위: month 또는 week
        "rollups": rows("rollups"),                              # 출시부터 지금까지
        "recent": rows("recent"),                                # 최근 30일, 하루 단위
    }


def parse_news(payload):
    """Steam 공지 목록을 [{date, title, url, patch}]로 바꾼다. 개발사가 올린 공지만 남기고 날짜순으로 놓는다.

    patch는 개발사가 '패치 노트'로 표시한 공지다. 표시한 공지가 하나도 없는 게임은 화면이 공지 전체를 보여준다.
    """
    out = []
    for item in ((payload or {}).get("appnews") or {}).get("newsitems") or []:
        if item.get("feedname") != "steam_community_announcements" or not item.get("date"):
            continue
        out.append({
            "date": datetime.fromtimestamp(int(item["date"]), timezone.utc).strftime("%Y-%m-%d"),
            "title": str(item.get("title") or "").strip(),
            "url": item.get("url") or "",
            "patch": "patchnotes" in (item.get("tags") or []),
        })
    return sorted(out, key=lambda e: e["date"])


def fetch(app_id):
    import httpx
    response = httpx.get(URL.format(app_id=app_id), params={"l": "english", "review_score_preference": 0}, timeout=15.0)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise ValueError("Steam이 이 게임의 리뷰 추이를 주지 않았습니다")
    data = parse(payload)
    # 공지를 못 받아도 추이는 보여준다
    try:
        news = httpx.get(NEWS_URL, params={"appid": app_id, "count": 200, "maxlength": 1,
                                           "feeds": "steam_community_announcements"}, timeout=15.0)
        news.raise_for_status()
        data["events"] = parse_news(news.json())
    except Exception:
        data["events"] = []
    return data


def load(folder):
    path = os.path.join(folder, FILENAME)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(folder, data):
    with open(os.path.join(folder, FILENAME), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
