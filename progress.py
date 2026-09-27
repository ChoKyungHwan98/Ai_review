"""분석 진행 상황을 게임 폴더의 progress.json에 남긴다. 화면이 1.5초마다 읽어 단계별 막대를 그린다.

stage: collect(리뷰 모으기) · topics(주제 찾기) · classify(리뷰 분류) · deep(불만 원인) · finish(점검·요약)
"""
import json
import os
import time

from config import cfg

STAGES = ("collect", "topics", "classify", "deep", "finish")
_last = {"at": 0.0, "key": None}


def report(stage, done=None, total=None, force=False):
    """단계와 건수를 기록한다. 같은 단계의 잦은 갱신은 0.5초에 한 번만 쓴다."""
    now = time.monotonic()
    key = (stage, done == total)
    if not force and key == _last["key"] and now - _last["at"] < 0.5:
        return
    _last.update(at=now, key=key)
    data = {"stage": stage, "done": done, "total": total}
    path = cfg.project_file("progress.json")
    try:
        with open(path + ".tmp", "w", encoding="utf-8") as stream:
            json.dump(data, stream)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


def read(folder):
    try:
        with open(os.path.join(folder, "progress.json"), encoding="utf-8") as stream:
            data = json.load(stream)
        return data if data.get("stage") in STAGES else None
    except (OSError, ValueError):
        return None
