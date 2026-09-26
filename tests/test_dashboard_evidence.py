import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dashboard_evidence import build_evidence, evidence_page, review_hours


class DashboardEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.rows = [
            {"recommendationid": "1", "content": "좋지만 저장이 안 됩니다", "voted_up": "1",
             "playtime_at_review_min": "0", "playtime_forever_min": "10000", "votes_up": "2"},
            {"recommendationid": "2", "content": "저장 오류", "voted_up": "0",
             "playtime_at_review_min": "120", "playtime_forever_min": "120", "votes_up": "5"},
            {"recommendationid": "3", "content": "좋음", "voted_up": "1",
             "playtime_at_review_min": "", "playtime_forever_min": "6000", "votes_up": "0"},
            {"recommendationid": "4", "content": "재미있다", "voted_up": "1",
             "playtime_at_review_min": "6000", "playtime_forever_min": "6000", "votes_up": "0"},
        ]
        self.analyses = [
            {"id": "1", "up": 0, "s": "M", "t": [["저장", "N"], ["저장", "N"], ["건축", "P"], ["건축", "N"]], "f": ["몰두", "몰두"]},
            {"id": "2", "s": "N", "t": [["저장", "N"]]},
            {"id": "4", "s": "P", "t": [["건축", "P"]], "f": ["도전"]},
        ]
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        with (self.folder / "reviews.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)
        (self.folder / "analysis_v3.jsonl").write_text("\n".join(json.dumps(a) for a in self.analyses), encoding="utf-8")

    def test_zero_hours_is_not_replaced_by_lifetime_hours(self):
        self.assertEqual(review_hours(self.rows[0]), 0)
        self.assertIsNone(review_hours(self.rows[2]))
        e = build_evidence(self.folder, 42)
        self.assertEqual([c["n"] for c in e["cohorts"]], [1, 1, 0, 1])
        self.assertEqual(e["counts"]["unknown_playtime"], 1)

    def test_topic_counts_are_unique_and_distinct_from_recommendation(self):
        e = build_evidence(self.folder, 42)
        self.assertEqual(e["mood"], {"P": 1, "M": 1, "N": 1, "U": 0})
        storage = next(t for t in e["themes"] if t["name"] == "저장")
        building = next(t for t in e["themes"] if t["name"] == "건축")
        self.assertEqual(storage["neg"], 2)
        self.assertEqual(storage["negative_recommended"], 1)
        self.assertEqual(building["mentions"], 2)
        self.assertEqual(building["pos"] + building["neg"], 3)
        self.assertEqual(e["counts"]["complaint_reviews"], 2)
        self.assertEqual(e["counts"]["recommended_complaints"], 1)
        self.assertEqual(storage["exclusion_delta"], 25.0)

    def test_heatmap_and_fun_use_their_own_denominators(self):
        e = build_evidence(self.folder, 42)
        storage = next(t for t in e["themes"] if t["name"] == "저장")
        self.assertEqual(storage["cells"][0], {"count": 1, "denominator": 1, "rate": 100.0})
        self.assertIsNone(storage["cells"][2]["rate"])
        self.assertEqual(e["fun_denominator"], 2)
        self.assertTrue(all(f["share"] == 50 for f in e["fun"]))

    def test_evidence_pagination_and_sentiment_match_counts(self):
        page = evidence_page(self.folder, 42, "저장", "N")
        self.assertEqual(page["total"], 2)
        self.assertEqual([r["id"] for r in page["reviews"]], ["2", "1"])
        self.assertEqual(evidence_page(self.folder, 42, "저장", "P")["total"], 0)
        self.assertEqual(evidence_page(self.folder, 42, "저장", "N", 2)["reviews"], [])
        self.assertIsNone(evidence_page(self.folder, 42, "없는 주제"))

    def test_partial_lines_and_unmatched_ids_are_reported(self):
        with (self.folder / "analysis_v3.jsonl").open("a", encoding="utf-8") as f:
            f.write('\n{"id":"missing"}\n{"id":')
        e = build_evidence(self.folder, 42)
        self.assertEqual(e["counts"]["skipped_analysis"], 2)
        self.assertEqual(e["counts"]["analyzed"], 3)

    def test_deep_analysis_recounts_saved_results_without_ai(self):
        complaints = [
            {"id": "1", "p": [{"t": "저장", "prob": "세이브 파일이 날아감", "why": "서버 오류", "fix": "자동 저장 추가해주세요"}]},
            {"id": "2", "p": [{"t": "저장", "prob": "세이브 파일 손상", "why": "", "fix": "자동 저장 추가해주세요"},
                              {"t": "저장", "prob": "", "why": "", "fix": "버그 수정"}]},
        ]
        (self.folder / "complaints_v3.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in complaints), encoding="utf-8")
        deep = build_evidence(self.folder, 42)["deep"]
        storage = next(c for c in deep["causes"] if c["theme"] == "저장")
        self.assertEqual(storage["reviews"], 2)
        self.assertEqual(storage["terms"][0]["word"], "세이브")
        self.assertEqual({t["word"] for t in storage["terms"]}, {"세이브", "파일"})
        # 2번만 비추천이고 2시간 플레이 → 초반 이탈
        self.assertEqual(deep["churn"]["early_n"], 1)
        self.assertEqual(deep["churn"]["topics"][0], {"name": "저장", "early": 1, "later": 0, "early_share": 100.0, "later_share": None})
        agreed = next(t for t in deep["agreed"]["topics"] if t["name"] == "저장")
        self.assertEqual(agreed["votes"], 7)
        self.assertEqual(deep["agreed"]["reviews"][0]["id"], "2")
        self.assertEqual(deep["wants"], [{"text": "자동 저장 추가해주세요", "theme": "저장", "count": 2, "votes": 7}])

    def test_deep_analysis_without_complaint_file(self):
        deep = build_evidence(self.folder, 42)["deep"]
        self.assertFalse(deep["has_complaints"])
        self.assertEqual(deep["wants"], [])
        self.assertTrue(all(c["terms"] == [] for c in deep["causes"]))

    def test_empty_and_missing_sources_are_explicit(self):
        self.analyses = []
        self.write()
        e = build_evidence(self.folder, 42)
        self.assertEqual(e["themes"], [])
        self.assertEqual(e["fun"], [])
        self.assertEqual(e["mood"], {"P": 0, "M": 0, "N": 0, "U": 0})
        self.assertEqual(e["counts"]["complaint_reviews"], 0)
        self.assertIsNone(build_evidence(self.folder / "absent", 42))


if __name__ == "__main__":
    unittest.main()
