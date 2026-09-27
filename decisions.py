"""사람의 결정: 주제 다듬기, 주제별 결론, 분석 설계서. AI를 부르지 않는다.

게임 폴더의 decisions.json 하나에 저장한다.
  alias     {원래 주제: 새 이름 | 합칠 주제 | null(숨김)}
  verdicts  {주제: {"choice": fix|watch|ignore, "memo": "", "at": ""}}
  log       사람이 바꾼 내용의 기록
"""
import json
from datetime import datetime
from pathlib import Path

FILE = "decisions.json"
CHOICES = {"fix": "고친다", "watch": "지켜본다", "ignore": "무시한다"}
LANGS = {"koreana": "한국어", "english": "영어", "japanese": "일본어", "schinese": "중국어 간체",
         "tchinese": "중국어 번체", "all": "모든 언어"}


def load(folder):
    path = Path(folder) / FILE
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    return {"alias": dict(data.get("alias") or {}), "verdicts": dict(data.get("verdicts") or {}),
            "log": list(data.get("log") or [])}


def save(folder, data):
    (Path(folder) / FILE).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve(name, alias):
    """합치기·이름 바꾸기를 따라가 최종 이름을 돌려준다. 숨긴 주제는 None."""
    seen = set()
    while name in alias and name not in seen:
        seen.add(name)
        name = alias[name]
        if name is None:
            return None
    return name


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def edit_topic(folder, action, source, target=None, names=()):
    """action: merge(다른 주제에 합치기) · rename(이름 바꾸기) · hide(숨기기) · restore(되돌리기)."""
    data = load(folder)
    alias = data["alias"]
    source = (source or "").strip()
    target = (target or "").strip()
    current = {resolve(n, alias) for n in names} - {None}
    if action == "restore":
        if source not in alias:
            raise ValueError("되돌릴 변경이 없습니다")
        alias.pop(source)
        text = f"'{source}' 변경을 되돌림"
    else:
        if source not in current:
            raise ValueError("지금 목록에 없는 주제입니다")
        if action == "hide":
            alias[source] = None
            text = f"'{source}' 주제를 숨김"
        elif action in ("merge", "rename"):
            if not target or target == source or len(target) > 20:
                raise ValueError("새 이름이나 합칠 주제를 확인하세요")
            if action == "merge" and target not in current:
                raise ValueError("합칠 주제가 목록에 없습니다")
            if action == "rename" and target in current:
                raise ValueError("같은 이름의 주제가 이미 있습니다. 합치기를 쓰세요")
            alias[source] = target
            if source in data["verdicts"] and target not in data["verdicts"]:
                data["verdicts"][target] = data["verdicts"].pop(source)
            text = f"'{source}'을(를) '{target}'에 합침" if action == "merge" else f"'{source}' 이름을 '{target}'(으)로 바꿈"
        else:
            raise ValueError("지원하지 않는 작업입니다")
    data["log"].append({"at": now(), "step": "topics", "text": text})
    save(folder, data)
    return data


def set_verdict(folder, theme, choice, memo=""):
    data = load(folder)
    theme = (theme or "").strip()
    memo = (memo or "").strip()[:300]
    if not theme:
        raise ValueError("주제를 고르세요")
    if choice and choice not in CHOICES:
        raise ValueError("결론은 고친다·지켜본다·무시한다 중 하나입니다")
    if choice:
        data["verdicts"][theme] = {"choice": choice, "memo": memo, "at": now()}
        data["log"].append({"at": now(), "step": "verdict", "text": f"'{theme}' → {CHOICES[choice]}" + (f" · {memo}" if memo else "")})
    elif data["verdicts"].pop(theme, None) is not None:
        data["log"].append({"at": now(), "step": "verdict", "text": f"'{theme}' 결론을 지움"})
    save(folder, data)
    return data


def design_log(data, sample_design, counts, usage, n_ai_topics, game=""):
    """분석 설계서: 무엇을 · 얼마나 · 무엇으로 · 어떻게 나눴고 · 무엇을 기준으로 · 무엇을 결정했나. who = 사람 | AI | 규칙."""
    params = (sample_design or {}).get("params") or {}
    design = (sample_design or {}).get("design") or {}
    counts = counts or {}
    since = params.get("since")
    rows = [{
        "step": "무엇을", "who": "사람",
        "text": " · ".join(x for x in [game, LANGS.get(params.get("language"), params.get("language") or ""),
                                         f"{since.replace('-', '.')} 이후" if since else "전체 기간",
                                         "공감순" if params.get("sort") == "helpful" else "최신순"] if x),
    }]
    planned = design.get("n_total")
    target = params.get("target_error_pct")
    how_much = []
    if planned:
        how_much.append(f"{planned:,}건 계획" + (f" (목표 오차 ±{target}%)" if target else ""))
    if counts.get("collected") is not None:
        how_much.append(f"{counts['collected']:,}건 수집")
    rows.append({"step": "얼마나", "who": "사람", "text": " → ".join(how_much) or "기록 없음"})
    if counts.get("collected") is not None and counts.get("analyzed") is not None:
        rows.append({"step": "분석 대상", "who": "규칙",
                     "text": f"너무 짧은 리뷰 {counts['collected'] - counts['analyzed']:,}건 제외 → AI 분석 {counts['analyzed']:,}건"})
    if (usage or {}).get("model"):
        rows.append({"step": "분석 모델", "who": "사람", "text": usage["model"]})
    edits = [e["text"] for e in data.get("log", []) if e.get("step") == "topics"]
    rows.append({"step": "주제 나누기", "who": "AI + 사람" if data.get("alias") else "AI",
                 "text": f"AI가 주제 {n_ai_topics}개를 제안" + (f" · 사람이 {len(data['alias'])}건 다듬음" if data.get("alias") else " · 수정 없음"),
                 "details": edits[-8:]})
    rows.append({"step": "판단 기준", "who": "규칙",
                 "text": "불만이 칭찬보다 많으면 불만 우세 · 지도 기준선은 언급 수 중앙값과 불만 50%"})
    verdicts = data.get("verdicts") or {}
    rows.append({"step": "결론", "who": "사람" if verdicts else "사람 (대기)",
                 "text": f"주제 {len(verdicts)}개에 결론을 남김" if verdicts else "아직 내린 결론이 없습니다. 진단 요약에서 주제를 고르고 결론을 남기세요",
                 "details": [f"{name} → {CHOICES[v['choice']]}" + (f" · {v['memo']}" if v.get("memo") else "")
                             for name, v in verdicts.items() if v.get("choice") in CHOICES]})
    return rows
