import asyncio
import copy
import csv
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_reviews_v3 as analyzer
import build_insights_v5 as insights
import pipeline
from token_budget import estimate_remaining


class FakeConfig:
    MIN_REVIEW_LEN = 8
    MODEL = "test-model"
    MODEL_COST_INPUT = 0.1
    MODEL_COST_OUTPUT = 0.4
    BUDGET_USD = 1.0

    def __init__(self, folder):
        self.folder = folder

    def project_dir(self, app_id=None):
        return str(self.folder)


class TokenOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_short_complaints_are_classified_without_treating_vote_as_sentiment(self):
        self.assertTrue(analyzer.should_classify({"content": "노잼", "voted_up": "0"}))
        self.assertTrue(analyzer.should_classify({"content": "버그", "voted_up": "1"}))
        self.assertFalse(analyzer.should_classify({"content": "좋아", "voted_up": "1"}))
        self.assertFalse(analyzer.should_classify({"content": "ㅋ", "voted_up": "0"}))
        self.assertTrue(analyzer.needs_deep({"s": "P", "t": []},
                                             {"content": "좋은 점도 있지만 많이 불편합니다", "voted_up": "0"}))

    def test_estimate_uses_pending_ids_and_deep_work(self):
        rows = [
            {"recommendationid": "1", "content": "저장 문제가 계속 반복됩니다"},
            {"recommendationid": "2", "content": "그래픽과 음악이 정말 좋습니다"},
            {"recommendationid": "3", "content": "새로운 리뷰가 추가되었습니다"},
            {"recommendationid": "4", "content": "좋음"},
        ]
        with (self.folder / "reviews.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        (self.folder / "analysis_v3.jsonl").write_text(
            '\n'.join(json.dumps(x) for x in ({"id": "1", "s": "N", "t": []}, {"id": "2", "s": "P", "t": []})),
            encoding="utf-8")
        (self.folder / "themes_v3.json").write_text("[]", encoding="utf-8")
        estimate = estimate_remaining(FakeConfig(self.folder))
        self.assertEqual((estimate["total_reviews"], estimate["short_reviews"], estimate["to_analyze"], estimate["to_deep"]),
                         (4, 1, 1, 1))
        self.assertGreater(estimate["estimated_input_tokens"], 0)
        (self.folder / "complaints_v3.jsonl").write_text('{"id":"1","p":[]}', encoding="utf-8")
        estimate = estimate_remaining(FakeConfig(self.folder))
        self.assertEqual(estimate["to_deep"], 0)
        self.assertEqual(estimate["to_analyze"], 1)

    def test_incomplete_deep_batch_is_not_silent(self):
        rows = [{"recommendationid": str(i), "content": "저장 오류가 여러 번 반복됩니다"} for i in (1, 2)]
        classified = {str(i): {"s": "N", "t": []} for i in (1, 2)}
        fake_answer = [{"id": "1", "p": []}]
        with patch.object(analyzer, "path", side_effect=lambda name: str(self.folder / name)), \
             patch.object(analyzer, "ask", new=AsyncMock(return_value=fake_answer)):
            with self.assertRaisesRegex(RuntimeError, "1건이 누락"):
                asyncio.run(analyzer.dig_complaints(None, rows, classified, []))
        self.assertEqual(len((self.folder / "complaints_v3.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_deep_batch_retries_only_missing_review(self):
        rows = [{"recommendationid": str(i), "content": "저장 오류가 여러 번 반복됩니다"} for i in (1, 2)]
        classified = {str(i): {"s": "N", "t": []} for i in (1, 2)}
        answers = [[{"id": "1", "p": []}], [{"id": "2", "p": []}]]
        with patch.object(analyzer, "path", side_effect=lambda name: str(self.folder / name)), \
             patch.object(analyzer, "ask", new=AsyncMock(side_effect=answers)) as ask:
            result = asyncio.run(analyzer.dig_complaints(None, rows, classified, []))
        self.assertEqual(set(result), {"1", "2"})
        self.assertEqual(ask.await_count, 2)

    def test_identical_summary_reuses_saved_answer(self):
        result = {"lifts": [{"name": "건축", "pos": 3}], "drags": [], "fun": [], "playtime": [], "rates": {"steam": 90}}
        with patch.object(insights, "path", side_effect=lambda name: str(self.folder / name)), \
             patch.object(insights, "build", side_effect=lambda: (copy.deepcopy(result), {})), \
             patch.object(insights.cfg, "get_game_name", return_value="다른 게임"), \
             patch.object(insights, "ask_summary", return_value=({"summary": "건축을 좋아합니다.", "actions": []},
                                                               {"prompt_tokens": 100, "completion_tokens": 20})) as ask:
            first = insights.main()
            second = insights.main()
        self.assertEqual(ask.call_count, 1)
        self.assertFalse(first["summary_cached"])
        self.assertTrue(second["summary_cached"])
        self.assertEqual(json.loads((self.folder / "usage_v3.json").read_text(encoding="utf-8"))["D"]["calls"], 1)

    def test_usage_counters_reset_between_runs(self):
        analyzer.USAGE["A"] = {"calls": 99, "input": 999, "output": 999}
        with patch.object(analyzer, "API_KEY", "test"), \
             patch.object(analyzer, "load_reviews", return_value=([], [])), \
             patch.object(analyzer, "find_themes", new=AsyncMock(return_value=[])), \
             patch.object(analyzer, "classify", new=AsyncMock(return_value={})), \
             patch.object(analyzer, "dig_complaints", new=AsyncMock(return_value={})), \
             patch.object(analyzer, "save_usage"):
            asyncio.run(analyzer.run_all())
        self.assertEqual(analyzer.USAGE["A"], {"calls": 0, "input": 0, "output": 0})

    def test_game_runs_do_not_overlap_shared_configuration(self):
        active = 0
        peak = 0
        guard = threading.Lock()

        def fake_run(*args):
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
            time.sleep(0.02)
            with guard:
                active -= 1
            return {}

        with patch.object(pipeline, "_run_pipeline_unlocked", side_effect=fake_run):
            threads = [threading.Thread(target=pipeline.run_pipeline, kwargs={"app_id": i}) for i in (1, 2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(peak, 1)


if __name__ == "__main__":
    unittest.main()
