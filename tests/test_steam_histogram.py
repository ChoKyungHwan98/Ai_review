import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import steam_histogram


class SteamHistogramTests(unittest.TestCase):
    def test_parse_keeps_counts_and_converts_dates(self):
        payload = {"success": 1, "results": {
            "rollup_type": "month",
            "rollups": [{"date": 1704067200, "recommendations_up": 146750, "recommendations_down": 9677}],
            "recent": [{"date": 1788393600, "recommendations_up": 238, "recommendations_down": 16}],
        }}
        data = steam_histogram.parse(payload, now=datetime(2026, 10, 2, 18, 30))
        self.assertEqual(data["fetched_at"], "2026-10-02 18:30")
        self.assertEqual(data["rollup_type"], "month")
        self.assertEqual(data["rollups"], [{"date": "2024-01-01", "up": 146750, "down": 9677}])
        self.assertEqual(data["recent"], [{"date": "2026-09-03", "up": 238, "down": 16}])

    def test_parse_empty_payload(self):
        data = steam_histogram.parse({})
        self.assertEqual((data["rollups"], data["recent"]), ([], []))

    def test_parse_news_keeps_developer_announcements_in_date_order(self):
        payload = {"appnews": {"newsitems": [
            {"date": 1788480000, "title": " v0.6.1 ", "url": "u2", "feedname": "steam_community_announcements", "tags": ["patchnotes"]},
            {"date": 1788393600, "title": "Sale", "url": "u1", "feedname": "steam_community_announcements"},
            {"date": 1788393600, "title": "Press", "url": "u0", "feedname": "PC Gamer"},
        ]}}
        self.assertEqual(steam_histogram.parse_news(payload), [
            {"date": "2026-09-03", "title": "Sale", "url": "u1", "patch": False},
            {"date": "2026-09-04", "title": "v0.6.1", "url": "u2", "patch": True},
        ])
        self.assertEqual(steam_histogram.parse_news({}), [])

    def test_save_then_load(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(steam_histogram.load(folder))
            steam_histogram.save(folder, {"fetched_at": "x", "rollups": [], "recent": []})
            self.assertEqual(steam_histogram.load(folder)["fetched_at"], "x")


if __name__ == "__main__":
    unittest.main()
