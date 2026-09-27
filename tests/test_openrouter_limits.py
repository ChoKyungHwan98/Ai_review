import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import analyze_reviews_v3 as analyzer
import openrouter_limits as limits
import progress
from config import cfg


def ok(items):
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"items": items})}}],
                                     "usage": {"prompt_tokens": 10, "completion_tokens": 5}})


class FreeModelLimitTests(unittest.TestCase):
    """무료 모델은 분당 20회 안에서 천천히 보내고, 하루 한도에 닿으면 이어하기 안내와 함께 멈춘다."""

    def setUp(self):
        self.saved = (getattr(cfg, "MODEL_FREE", False), cfg.MODEL)
        limits._next[0] = 0.0

    def tearDown(self):
        cfg.MODEL_FREE, cfg.MODEL = self.saved

    def call(self, responses):
        queue = list(responses)
        transport = httpx.MockTransport(lambda request: queue.pop(0))

        async def run():
            async with httpx.AsyncClient(transport=transport) as client:
                return await analyzer.ask(client, "B", "s", "u", 100)
        async def no_wait(*_):
            return None
        with patch("asyncio.sleep", new=no_wait):
            return asyncio.run(run()), queue

    def test_free_models_are_paced_and_paid_models_are_not(self):
        cfg.MODEL_FREE = True
        delays = [limits._delay() for _ in range(3)]
        self.assertEqual(delays[0], 0)
        self.assertAlmostEqual(delays[2] - delays[1], limits.GAP, places=1)
        self.assertEqual(limits.concurrency(3), 1)
        cfg.MODEL_FREE, cfg.MODEL = False, "google/gemini-2.5-flash-lite"
        self.assertEqual(limits._delay(), 0)
        self.assertEqual(limits.concurrency(3), 3)

    def test_rate_limit_waits_then_succeeds(self):
        cfg.MODEL_FREE = False
        result, left = self.call([httpx.Response(429, headers={"retry-after": "1"}, text="slow down"), ok([{"id": "1"}])])
        self.assertEqual(result, [{"id": "1"}])
        self.assertEqual(left, [])

    def test_daily_limit_stops_with_resume_message(self):
        cfg.MODEL_FREE = False
        with self.assertRaises(analyzer.FatalApiError) as caught:
            self.call([httpx.Response(429, text='{"error":{"message":"Rate limit exceeded: free-models-per-day"}}')])
        self.assertIn("이어서", str(caught.exception))


class ProgressTests(unittest.TestCase):
    def test_progress_is_written_and_read_per_game(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(cfg, "project_file", lambda name: str(Path(folder) / name)):
            progress.report("classify", 3, 10, force=True)
            self.assertEqual(progress.read(folder), {"stage": "classify", "done": 3, "total": 10})
            (Path(folder) / "progress.json").write_text('{"stage":"x"}', encoding="utf-8")
            self.assertIsNone(progress.read(folder))


if __name__ == "__main__":
    unittest.main()
