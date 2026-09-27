import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import main


class DecisionApiTests(unittest.TestCase):
    """주제 다듬기와 내 결론이 화면 데이터와 분석 설계서에 그대로 반영되는지."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        rows = [{"recommendationid": "1", "content": "렉이 심함", "voted_up": "0", "playtime_at_review_min": "60", "votes_up": "3"},
                {"recommendationid": "2", "content": "최적화 별로", "voted_up": "1", "playtime_at_review_min": "600", "votes_up": "1"}]
        with (self.folder / "reviews.csv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        (self.folder / "analysis_v3.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
            {"id": "1", "s": "N", "t": [["렉", "N"]]}, {"id": "2", "s": "M", "t": [["최적화", "N"], ["최적화", "P"]]}]), encoding="utf-8")
        (self.folder / "analysis_v3.csv").write_text("recommendationid,keywords\n1,렉@technical\n2,최적화@technical\n", encoding="utf-8-sig")
        (self.folder / "insights_v5.json").write_text(json.dumps({
            "themes": [{"name": "렉", "desc": "끊김"}, {"name": "최적화", "desc": "성능"}],
            "actions": [{"theme": "렉", "prob": "끊김"}], "usage": {"model": "m"}}, ensure_ascii=False), encoding="utf-8")
        self.patch = patch.object(main, "_game_dir", return_value=str(self.folder))
        self.patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_merge_then_verdict_flow(self):
        r = self.client.post("/dashboard/topics", json={"app_id": 7, "action": "merge", "source": "렉", "target": "최적화"})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post("/dashboard/verdict", json={"app_id": 7, "theme": "최적화", "choice": "fix", "memo": "거점 렉"})
        self.assertEqual(r.status_code, 200, r.text)
        data = self.client.get("/dashboard/data/v5?app_id=7").json()
        self.assertEqual([t["name"] for t in data["evidence"]["themes"]], ["최적화"])
        self.assertEqual(data["evidence"]["themes"][0]["neg"], 2)
        self.assertEqual([t["name"] for t in data["themes"]], ["최적화"])
        self.assertEqual(data["actions"][0]["theme"], "최적화")
        self.assertEqual([r["keywords"] for r in data["reviews"]], ["최적화@technical", "최적화@technical"])
        steps = {row["step"]: row for row in data["design_log"]}
        self.assertEqual(steps["주제 나누기"]["who"], "AI + 사람")
        self.assertEqual(steps["결론"]["details"], ["최적화 → 고친다 · 거점 렉"])

    def test_bad_requests_are_rejected(self):
        self.assertEqual(self.client.post("/dashboard/topics", json={"app_id": 7, "action": "merge", "source": "렉", "target": "없음"}).status_code, 422)
        self.assertEqual(self.client.post("/dashboard/verdict", json={"app_id": 7, "theme": "렉", "choice": "maybe"}).status_code, 422)


if __name__ == "__main__":
    unittest.main()
