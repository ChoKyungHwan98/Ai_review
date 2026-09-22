"""리뷰 분석 API - FastAPI 메인 앱

실행: uvicorn main:app --host 127.0.0.1 --port 8765
문서: http://127.0.0.1:8765/docs
대시보드: http://127.0.0.1:8765/dashboard

데이터 출처 및 라이선스:
- Steam 리뷰 데이터: Valve Steam Web API (공개 API, 비상업적 분석 목적)
- LLM 분석: OpenRouter API (Google Gemini 2.0 Flash)
- 본 프로젝트는 교육·포트폴리오 목적으로 제작되었습니다.
"""

import os, csv, json
import httpx
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import cfg

from models import (
    ReviewCreate, ReviewResponse,
    AnalyzeRequest, AnalysisResponse,
    StatsResponse,
)
from database import (
    init_database,
    create_review, get_review, get_all_reviews,
    save_analysis, get_analysis,
    get_stats,
)
from analyzer import analyze_review


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 DB 초기화
    init_database()
    yield


app = FastAPI(
    title="리뷰 분석 API",
    description="게임 리뷰를 저장하고 LLM으로 분석하는 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 — 외부 프론트엔드 접근 허용 (강의 session-38 API 보안)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 화면 HTML은 주소가 고정이라 Cache-Control이 없으면 브라우저 휴리스틱 캐시가 걸린다.
# 스튜디오의 WebView2가 옛 화면을 계속 띄우게 되므로 항상 서버에 확인하게 한다.
NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


@app.get("/", summary="메인 화면", include_in_schema=False)
def root():
    return FileResponse(os.path.join(cfg.PROGRAM_DIR, "static", "index.html"), headers=NO_CACHE_HEADERS)


@app.get(
    "/reviews",
    response_model=list[ReviewResponse],
    summary="리뷰 목록 조회",
    description="저장된 모든 리뷰를 최신순으로 반환합니다.",
)
def list_reviews():
    return get_all_reviews()


@app.post(
    "/reviews",
    response_model=ReviewResponse,
    summary="리뷰 추가",
    description="새 리뷰를 DB에 저장하고 저장된 리뷰를 반환합니다.",
)
def add_review(review: ReviewCreate):
    review_id = create_review(content=review.content, game_name=review.game_name)
    return get_review(review_id)


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="분석 실행",
    description="특정 리뷰를 LLM(OpenRouter)에 보내 감성/키워드/확신도를 분석합니다.",
)
def run_analysis(request: AnalyzeRequest):
    review = get_review(request.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다")

    try:
        analysis = analyze_review(review["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")

    save_analysis(
        review_id=request.review_id,
        sentiment=analysis["sentiment"],
        keywords=analysis["keywords"],
        confidence=analysis["confidence"],
    )
    return get_analysis(request.review_id)


@app.get(
    "/analysis/{review_id}",
    response_model=AnalysisResponse,
    summary="분석 결과 조회",
    description="특정 리뷰 ID에 대한 분석 결과를 조회합니다.",
)
def get_analysis_result(review_id: int):
    result = get_analysis(review_id)
    if not result:
        raise HTTPException(status_code=404, detail="분석 결과가 없습니다.")
    return result


@app.get(
    "/stats",
    response_model=StatsResponse,
    summary="통계 조회",
    description="전체 리뷰 수, 분석된 리뷰 수, 감성별 분포를 반환합니다.",
)
def get_statistics():
    return get_stats()


# ====================================================================
# 대시보드 (Tailwind + Chart.js 기반 웹 어플리케이션 UI)
# ====================================================================

# 정적 파일 마운트 (프로그램 폴더 안의 UI만 제공)
STATIC_DIR = os.path.join(cfg.PROGRAM_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/dashboard", response_class=HTMLResponse, summary="대시보드 페이지", include_in_schema=False)
def dashboard_page():
    """리뷰 분석 대시보드 (어플리케이션 UI)"""
    path = os.path.join(cfg.PROGRAM_DIR, "static", "dashboard.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="dashboard.html 없음")
    return FileResponse(path, headers=NO_CACHE_HEADERS)


# ── 멀티게임 관리 API ─────────────────────────────────────────────
GAMES_JSON = cfg.GAMES_JSON

def _load_games():
    if os.path.exists(GAMES_JSON):
        with open(GAMES_JSON, "r", encoding="utf-8") as f:
            return json.load(f).get("games", [])
    return []

def _save_games(games):
    os.makedirs(os.path.dirname(GAMES_JSON), exist_ok=True)
    with open(GAMES_JSON, "w", encoding="utf-8") as f:
        json.dump({"games": games}, f, ensure_ascii=False, indent=2)

def _game_dir(app_id):
    return cfg.project_dir(app_id)

def _game_file(app_id, filename):
    """Return a file from the one canonical 프로젝트/{app_id} store."""
    path = os.path.join(_game_dir(app_id), filename)
    return path if os.path.exists(path) else None


@app.get("/api/games", summary="분석된 게임 목록", include_in_schema=False)
def list_games():
    return {"games": _load_games()}


@app.delete("/api/games/{app_id}", summary="프로젝트 삭제", include_in_schema=False)
def trash_game(app_id: int):
    """프로젝트를 목록에서 빼고 폴더를 휴지통으로 옮깁니다.

    지우지 않고 옮기기만 하므로 사용자가 직접 되돌릴 수 있습니다.
    """
    games = _load_games()
    remaining = [game for game in games if str(game.get("app_id")) != str(app_id)]
    if len(remaining) == len(games):
        raise HTTPException(status_code=404, detail="해당 프로젝트를 찾지 못했습니다.")

    source = _game_dir(app_id)
    if os.path.isdir(source):
        trash_root = os.path.join(os.path.dirname(source), ".review-trash")
        os.makedirs(trash_root, exist_ok=True)
        destination = os.path.join(trash_root, f"{app_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        os.rename(source, destination)

    _save_games(remaining)
    return {"app_id": app_id, "remaining": len(remaining)}


@app.get("/api/games/search", summary="Steam 게임 검색", include_in_schema=False)
def search_steam_game(app_id: int):
    """Steam Store API에서 게임 정보를 조회합니다."""
    import httpx
    try:
        r = httpx.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": app_id, "l": "korean"},
            timeout=10.0,
        )
        data = r.json().get(str(app_id), {})
        if not data.get("success"):
            raise HTTPException(status_code=404, detail=f"App ID {app_id}를 찾을 수 없습니다")
        info = data["data"]
        return {
            "app_id": app_id,
            "name": info.get("name", f"App {app_id}"),
            "header_image": info.get("header_image", ""),
            "type": info.get("type", ""),
            "short_description": info.get("short_description", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/review-stats", summary="Steam 리뷰 모집단 통계", include_in_schema=False)
def review_population_stats(app_id: int):
    """Steam appreviews API로 한국어 리뷰 모집단 통계를 조회합니다."""
    import httpx, math
    url = f"https://store.steampowered.com/appreviews/{app_id}"
    try:
        # 한국어 리뷰 통계
        r_kr = httpx.get(url, params={
            "json": 1, "filter": "recent", "language": "koreana",
            "review_type": "all", "purchase_type": "all",
            "num_per_page": 0, "filter_offtopic_activity": 0,
        }, timeout=15.0)
        r_kr.raise_for_status()
        qs_kr = r_kr.json().get("query_summary", {})

        # 전체 언어 리뷰 통계
        r_all = httpx.get(url, params={
            "json": 1, "filter": "recent", "language": "all",
            "review_type": "all", "purchase_type": "all",
            "num_per_page": 0, "filter_offtopic_activity": 0,
        }, timeout=15.0)
        r_all.raise_for_status()
        qs_all = r_all.json().get("query_summary", {})

        total_kr = qs_kr.get("total_reviews", 0)
        pos_kr = qs_kr.get("total_positive", 0)
        neg_kr = qs_kr.get("total_negative", 0)
        total_all = qs_all.get("total_reviews", 0)
        score = qs_all.get("review_score_desc", "")

        # 실제 한국어 추천율(p) 적용 Cochran 표본 크기 산식
        p_val = pos_kr / total_kr if total_kr > 0 else 0.5
        # 지나치게 편향된 추천율(예: 99% 긍정)로 인한 극소 규모 왜곡 방지용 임계값 적용
        if p_val > 0.95: p_val = 0.95
        if p_val < 0.05: p_val = 0.05

        neg_rate_raw = neg_kr / total_kr if total_kr > 0 else 0.5

        def cochran_n(N, p=0.5, z=1.96, e=0.05):
            n0 = (z**2 * p * (1-p)) / (e**2)
            return math.ceil(n0 / (1 + (n0-1)/N)) if N > 0 else 0

        MIN_NEG = 100  # collect_reviews_v2.py 와 동일한 기준 (config.MIN_NEG_REVIEWS)

        sample_5pct = cochran_n(total_kr, p=p_val, e=0.05) if total_kr > 0 else 0
        sample_3pct = cochran_n(total_kr, p=p_val, e=0.03) if total_kr > 0 else 0

        # 부정 리뷰 최소 100건 확보에 필요한 총 수집량
        n_for_neg = math.ceil(MIN_NEG / neg_rate_raw) if neg_rate_raw > 0 else sample_5pct

        # 실제 수집 목표: 두 조건 중 더 큰 값 (collect_reviews_v2.py decide_sample_size와 동일)
        actual_5pct = min(max(sample_5pct, n_for_neg), total_kr)
        actual_3pct = min(max(sample_3pct, n_for_neg), total_kr)

        # 어떤 조건이 수집량을 결정했는지
        driver_5 = "MIN_NEG" if n_for_neg > sample_5pct else "Cochran"
        driver_3 = "MIN_NEG" if n_for_neg > sample_3pct else "Cochran"

        # 예상 비용 (Gemini 2.0 Flash 기준)
        avg_tokens = 1100  # 입출력 합산 평균
        cost_per_review = avg_tokens * (0.10 + 0.40) / 2 / 1_000_000
        est_cost_5 = round(actual_5pct * cost_per_review, 4)
        est_cost_3 = round(actual_3pct * cost_per_review, 4)

        return {
            "app_id": app_id,
            "global": {
                "total": total_all,
                "score": score,
            },
            "korean": {
                "total": total_kr,
                "positive": pos_kr,
                "negative": neg_kr,
                "pos_rate": round(pos_kr / total_kr * 100, 1) if total_kr > 0 else 0,
                "neg_rate": round(neg_kr / total_kr * 100, 1) if total_kr > 0 else 0,
            },
            "sample_design": {
                # Cochran 순수 통계 최솟값
                "sample_5pct": actual_5pct,
                "sample_3pct": actual_3pct,
                "est_cost_5pct": est_cost_5,
                "est_cost_3pct": est_cost_3,
                "p_applied": round(p_val, 4),
                "model": "google/gemini-2.0-flash-001",
                # 실제 수집 결정 근거
                "cochran_5pct": sample_5pct,
                "cochran_3pct": sample_3pct,
                "n_for_neg": n_for_neg,
                "min_neg_required": MIN_NEG,
                "driver_5pct": driver_5,
                "driver_3pct": driver_3,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models", summary="OpenRouter 모델 목록 조회", include_in_schema=False)
def get_openrouter_models():
    """OpenRouter API를 통해 최신 모델 정보를 가져와 동적으로 반환합니다."""
    import httpx
    curated = {
        "google/gemini-2.0-flash-001": "Google Gemini 2.0 Flash (초고속 & 초저가 - 추천)",
        "google/gemini-2.0-pro-exp-02-15": "Google Gemini 2.0 Pro Experimental (고성능 종합 추론)",
        "meta-llama/llama-3.3-70b-instruct": "Llama 3.3 70B Instruct (균형 잡힌 오픈소스)",
        "anthropic/claude-3.5-sonnet": "Anthropic Claude 3.5 Sonnet (최상급 감성 판단력)",
        "deepseek/deepseek-chat": "DeepSeek V3 (초고효율 가성비 모델)"
    }
    
    fallback = [
        {"id": "google/gemini-2.0-flash-001", "name": "Google Gemini 2.0 Flash (초고속 & 초저가 - 추천)", "input_cost": 0.075, "output_cost": 0.3},
        {"id": "google/gemini-2.0-pro-exp-02-15", "name": "Google Gemini 2.0 Pro Experimental (고성능 종합 추론)", "input_cost": 0.0, "output_cost": 0.0},
        {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B Instruct (균형 잡힌 오픈소스)", "input_cost": 0.23, "output_cost": 0.4},
        {"id": "anthropic/claude-3.5-sonnet", "name": "Anthropic Claude 3.5 Sonnet (최상급 감성 판단력)", "input_cost": 3.0, "output_cost": 15.0},
        {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3 (초고효율 가성비 모델)", "input_cost": 0.14, "output_cost": 0.28}
    ]
    
    try:
        r = httpx.get("https://openrouter.ai/api/v1/models", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            models = data.get("data", [])
            available_models = []
            for m in models:
                if m["id"] in curated:
                    pricing = m.get("pricing", {})
                    # pricing values are in dollars per token, convert to $ per 1M tokens
                    input_cost = float(pricing.get("prompt", 0)) * 1_000_000
                    output_cost = float(pricing.get("completion", 0)) * 1_000_000
                    available_models.append({
                        "id": m["id"],
                        "name": curated[m["id"]],
                        "input_cost": input_cost,
                        "output_cost": output_cost
                    })
            if available_models:
                # Sort available models in the original curated order
                curated_order = list(curated.keys())
                available_models.sort(key=lambda x: curated_order.index(x["id"]))
                return {"models": available_models}
    except Exception:
        pass
        
    return {"models": fallback}




@app.get("/api/reviews/download", summary="리뷰 CSV 다운로드", include_in_schema=False)
def download_reviews_csv(app_id: int = None):
    """수집된 리뷰 데이터를 CSV로 다운로드합니다."""
    from fastapi.responses import FileResponse
    import os
    
    csv_path = cfg.project_file("reviews.csv", app_id)
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="리뷰 CSV 파일을 찾을 수 없습니다")
    
    filename = f"reviews_{app_id or 'all'}.csv"
    return FileResponse(csv_path, media_type="text/csv", filename=filename)


@app.get("/api/analysis/download", summary="분석 결과 CSV 다운로드", include_in_schema=False)
def download_analysis_csv(app_id: int = None):
    """AI 분석 결과를 CSV로 다운로드합니다."""
    from fastapi.responses import FileResponse
    import os
    
    csv_path = cfg.project_file("analysis_v2.csv", app_id)
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="분석 CSV 파일을 찾을 수 없습니다")
    
    filename = f"analysis_{app_id or 'all'}.csv"
    return FileResponse(csv_path, media_type="text/csv", filename=filename)

@app.get("/dashboard/data/v4", summary="가중치 보정 대시보드 데이터", include_in_schema=False)
def dashboard_data_v4(app_id: int = None):
    """v4 가중치 보정 + 편향 점검 + 시계열 통합 JSON — 대시보드용 전처리 포함."""
    games = _load_games()
    if app_id is None:
        app_id = games[0]["app_id"] if games else 1623730
    
    game_info = next((g for g in games if g["app_id"] == app_id), None)
    game_name = (game_info.get("name_kr") or game_info.get("name")) if game_info else f"App {app_id}"

    insights_path = _game_file(app_id, "insights_v4.json")
    if not insights_path or not os.path.exists(insights_path):
        raise HTTPException(status_code=404, detail="insights_v4.json 없음 — 분석을 먼저 실행하세요")
    with open(insights_path, "r", encoding="utf-8") as f:
        ins = json.load(f)

    sd = {}
    sd_path = _game_file(app_id, "sample_design.json")
    if sd_path and os.path.exists(sd_path):
        with open(sd_path, "r", encoding="utf-8") as f:
            sd = json.load(f)

    ASPECTS = ["graphics", "gameplay", "story", "performance", "value"]
    ASPECT_KR = {
        "graphics": "그래픽", "gameplay": "게임플레이", "story": "스토리",
        "performance": "성능·버그", "value": "가격·가성비",
    }

    # ── ABSA 차트용 평탄화 (표본 + 가중치 보정) ──────────────────────────
    asp_s = ins["aspects"]["sample"]
    asp_w = ins["aspects"]["weighted"]
    aspects_pos, aspects_neu, aspects_neg = [], [], []
    aspects_pos_w, aspects_neu_w, aspects_neg_w = [], [], []
    for a in ASPECTS:
        s = asp_s.get(a, {}); w = asp_w.get(a, {})
        aspects_pos.append(s.get("POSITIVE", 0))
        aspects_neu.append(s.get("NEUTRAL", 0))
        aspects_neg.append(s.get("NEGATIVE", 0))
        aspects_pos_w.append(round(w.get("POSITIVE", 0)))
        aspects_neu_w.append(round(w.get("NEUTRAL", 0)))
        aspects_neg_w.append(round(w.get("NEGATIVE", 0)))

    # ── 감정 (표본 count + 가중치) ──────────────────────────────────────
    emotion = {k: v["sample"] for k, v in ins["emotion"].items()}
    emotion_weighted = {k: round(v["weighted"]) for k, v in ins["emotion"].items()}

    # ── 개선 우선순위 (테이블용 정규화) ─────────────────────────────────
    priority = [
        {
            "aspect": p["aspect"], "aspect_kr": p["aspect_kr"],
            "mentioned": round(p["mentioned_w"]), "pos": round(p["pos_w"]),
            "neg": round(p["neg_w"]), "neg_rate": p["neg_rate_w"],
            "mentioned_s": p["mentioned_s"], "pos_s": p["pos_s"],
            "neg_s": p["neg_s"], "neg_rate_s": p["neg_rate_s"],
        }
        for p in ins["aspects"]["priority"]
    ]

    # ── 플레이타임 구간별 추천률 (리뷰 목록에서 계산) ──────────────────
    bins = [("~1h", 0, 1), ("1~10h", 1, 10), ("10~50h", 10, 50),
            ("50~100h", 50, 100), ("100h+", 100, 1e9)]
    playtime = {label: {"n": 0, "pos": 0} for label, *_ in bins}
    for r in ins.get("reviews", []):
        h = float(r.get("playtime_h") or 0)
        vu = int(r.get("voted_up") or 0)
        for label, lo, hi in bins:
            if lo <= h < hi:
                playtime[label]["n"] += 1
                if vu: playtime[label]["pos"] += 1
                break
    for k in playtime:
        n_k = playtime[k]["n"]
        playtime[k]["recommend_rate"] = playtime[k]["pos"] / n_k * 100 if n_k else 0

    # ── 핵심 발견 ─────────────────────────────────────────────────────
    key_findings = []
    pri = priority
    # best_a: 긍정 평가 최다 영역 (이후 key_findings, recs 공통 사용)
    best_a = max(ASPECTS, key=lambda a: asp_w.get(a, {}).get("POSITIVE", 0))
    best_pos_w = round(asp_w.get(best_a, {}).get("POSITIVE", 0))
    if pri:
        w0 = pri[0]
        # 부정 원문 인용
        neg_evs = ins.get("aspect_evidence", {}).get(w0["aspect"], {}).get("negative") or []
        neg_quote = f'<span class="ev-quote">"{neg_evs[0][:45]}…"</span>' if neg_evs else ""
        # 샘플 vs 보정 격차
        s_neg = w0.get("neg_rate_s", 0)
        gap = w0["neg_rate"] - s_neg
        gap_note = f" (보정 후 {w0['neg_rate']:.0f}%로 실제론 더 심각)" if gap > 5 else ""
        key_findings.append({
            "type": "가장 시급한 개선점",
            "finding": (f"<b>{w0['aspect_kr']}</b> 불만이 비추천 리뷰의 "
                        f"<b>{w0['neg_rate']:.0f}%</b>에서 언급됨{gap_note}"),
            "impact": neg_quote or "QA 우선순위 1순위 배정 권고",
        })

    # 긍정 감정 + 부정 감정 비교 인사이트
    emo = ins["emotion"]
    joy_w   = emo.get("JOY", {}).get("weighted", 0)
    sat_w   = emo.get("SATISFACTION", {}).get("weighted", 0)
    anger_w = emo.get("ANGER", {}).get("weighted", 0)
    disap_w = emo.get("DISAPPOINTMENT", {}).get("weighted", 0)
    pos_emo_total = round(joy_w + sat_w)
    neg_emo_total = round(anger_w + disap_w)
    dominant_neg = "분노" if anger_w >= disap_w else "실망"
    dominant_pos = "기쁨" if joy_w >= sat_w else "만족"
    key_findings.append({
        "type": "감정 분포",
        "finding": (f"긍정 감정 <b>{pos_emo_total}건</b> ({dominant_pos} 주도) vs "
                    f"부정 감정 <b>{neg_emo_total}건</b> ({dominant_neg} 주도)"),
        "impact": (f"{dominant_neg}이 주된 불만 감정 — 구체적 트리거를 파악해 대응 메시지 준비 필요"
                   if neg_emo_total > 0 else "전반적으로 긍정 감정 우세"),
    })

    # 최고 강점 영역 인사이트
    pos_evs_best = ins.get("aspect_evidence", {}).get(best_a, {}).get("positive") or []
    pos_quote = f'<span class="ev-quote">"{pos_evs_best[0][:45]}…"</span>' if pos_evs_best else ""
    key_findings.append({
        "type": "핵심 강점",
        "finding": (f"<b>{ASPECT_KR.get(best_a, best_a)}</b>이 긍정 평가 최다 영역 "
                    f"(보정 후 약 <b>{best_pos_w}건</b>)"),
        "impact": pos_quote or "이 영역의 경험을 유지하는 것이 이탈 방지의 핵심",
    })

    # ── 추천 사항 ─────────────────────────────────────────────────────
    recs = []
    if pri:
        w0 = pri[0]
        evs = ins.get("aspect_evidence", {}).get(w0["aspect"], {}).get("negative") or []
        ev_snippet = f' 유저 표현: "{evs[0][:35]}"' if evs else ""
        # 2순위 문제도 함께 언급
        w1_note = f" + {pri[1]['aspect_kr']} 연계 개선 검토" if len(pri) > 1 else ""
        recs.append({"priority": 1,
            "action": f"{w0['aspect_kr']} 집중 개선{w1_note}",
            "reason": f"보정 후 부정률 {w0['neg_rate']:.0f}% — 실제 시장에서도 상위 불만 영역.{ev_snippet}"})

    recs.append({"priority": 2,
        "action": f"{ASPECT_KR.get(best_a, best_a)} 강점 유지 및 마케팅 활용",
        "reason": f"호평 최다 영역(약 {best_pos_w}건). 긍정 리뷰의 핵심 소구점으로 활용 가능"})

    # 감정 기반 추가 제안
    if neg_emo_total > 10:
        recs.append({"priority": 3,
            "action": f"{dominant_neg} 감정 트리거 분석 및 커뮤니케이션 대응",
            "reason": f"부정 감정 추정 {neg_emo_total}건 — 패치 노트·공지 톤앤매너 개선으로 완화 가능"})

    # ── Exec Summary ──────────────────────────────────────────────────
    n = ins["n_total"]
    pop = ins["population"]
    pop_pos_pct = pop["pos_rate"] * 100
    smp_pos_pct = ins["n_pos"] / n * 100 if n else 0
    sw = ins["sentiment"]["weighted"]
    sw_total = sum(sw.values()) or 1
    worst_kr = pri[0]["aspect_kr"] if pri else ""
    worst_rate_w = pri[0]["neg_rate"] if pri else 0
    best_kr = ASPECT_KR.get(best_a, "게임플레이")

    # 보정 후 추정 추천률
    wts_v4 = ins.get("weights", {})
    w_pos_v4 = wts_v4.get("w_pos", 1)
    w_neg_v4 = wts_v4.get("w_neg", 1)
    w_denom_v4 = w_pos_v4 * ins["n_pos"] + w_neg_v4 * ins["n_neg"]
    w_voted_pos_pct = (w_pos_v4 * ins["n_pos"]) / w_denom_v4 * 100 if w_denom_v4 > 0 else 0
    exec_title = (f"Steam 추천률 <b>{pop_pos_pct:.0f}%</b> · "
                  f"수집 데이터 추천률 <b>{smp_pos_pct:.0f}%</b> · "
                  f"보정 후 추정 <b>{w_voted_pos_pct:.0f}%</b>")
    exec_summary = (
        f"부정 리뷰를 깊이 분석하려고 비추천을 일부러 더 수집했습니다 (수집 데이터 추천률 {smp_pos_pct:.0f}%). "
        f"이 차이를 보정 계수로 바로잡은 결과 <b>{w_voted_pos_pct:.0f}%</b>로, "
        f"Steam 공식 추천률 {pop_pos_pct:.0f}%와 일치합니다. "
        f"가장 호평받은 영역은 <b>{best_kr}</b>, "
        f"가장 개선이 필요한 영역은 <b>{worst_kr}</b>(부정 {worst_rate_w:.0f}%)입니다."
    )

    # ── 표본 설계 요약 ────────────────────────────────────────────────
    pop_sd = sd.get("population", {})
    cs = sd.get("current_sample", {})
    rs = sd.get("required_sample_sizes", {})
    sample_design = {
        "pop_total": pop_sd.get("total", pop.get("total", 0)),
        "required_5pct": rs.get("e_5pct", 0),
        "analyzed": cs.get("analyzed", n),
        "error_pct": cs.get("margin_of_error_analyzed_pct", 0),
    }

    # ── 시계열 후처리: 표본 30건 미만 월은 신뢰도 낮음 → null 마스킹 ──
    tl_raw = ins.get("timeline", {})
    RELIABLE_N = 10
    tl_months = tl_raw.get("months", [])
    tl_totals = tl_raw.get("totals", [])
    def _is_reliable(i):
        return i < len(tl_totals) and (tl_totals[i] or 0) >= RELIABLE_N
    def _mask(arr):
        return [v if _is_reliable(i) else None for i, v in enumerate(arr)]
    reliable_months = {m for i, m in enumerate(tl_months) if _is_reliable(i)}
    cps_filtered = [cp for cp in tl_raw.get("change_points", [])
                    if cp.get("from_month") in reliable_months and cp.get("to_month") in reliable_months]
    timeline = {
        "months": tl_months,
        "totals": tl_totals,
        "sample_rates": _mask(tl_raw.get("sample_rates", [])),
        "weighted_rates": _mask(tl_raw.get("weighted_rates", [])),
        "moving_avg": _mask(tl_raw.get("moving_avg", [])),
        "change_points": cps_filtered,
        "reliable_threshold": RELIABLE_N,
    }

    # ── 데이터 품질 점검 (강의 session-16) ──────────────────────────
    quality_report = None
    qr_path = _game_file(app_id, "quality_report.json")
    if qr_path and os.path.exists(qr_path):
        try:
            with open(qr_path, "r", encoding="utf-8") as f:
                quality_report = json.load(f)
        except Exception:
            quality_report = None

    # ── 신뢰도 검증 (강의 session-44 "신뢰도 ≠ 정확도") ──────────
    verify_report = None
    vr_path = _game_file(app_id, "verify_report.json")
    if vr_path and os.path.exists(vr_path):
        try:
            with open(vr_path, "r", encoding="utf-8") as f:
                verify_report = json.load(f)
        except Exception:
            verify_report = None

    return {
        "game_name": game_name,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "quality_report": quality_report,
        "verify_report": verify_report,
        "n_total": n, "n_pos": ins["n_pos"], "n_neg": ins["n_neg"],
        "population": pop,
        "population_full": ins.get("population_full", {}),
        "weights": ins["weights"],
        "sentiment": ins["sentiment"]["sample"],
        "sentiment_weighted": ins["sentiment"]["weighted"],
        "emotion": emotion,
        "emotion_weighted": emotion_weighted,
        "aspects_kr": [ASPECT_KR[a] for a in ASPECTS],
        "aspects_pos": aspects_pos, "aspects_neu": aspects_neu, "aspects_neg": aspects_neg,
        "aspects_pos_w": aspects_pos_w, "aspects_neu_w": aspects_neu_w, "aspects_neg_w": aspects_neg_w,
        "playtime": playtime,
        "priority": priority,
        "aspect_evidence": ins.get("aspect_evidence", {}),
        "top_phrases_pos": ins.get("top_phrases_pos", []),
        "top_phrases_neg": ins.get("top_phrases_neg", []),
        "exec_title": exec_title,
        "exec_summary": exec_summary,
        "key_findings": key_findings,
        "recommendations": recs,
        "sample_design": sample_design,
        "sample_design_full": sd,
        "bias_audit": ins.get("bias_audit", {}),
        "timeline": timeline,
        "reviews": ins.get("reviews", []),
        "llm_hypothesis": ins.get("llm_hypothesis"),
        "llm_insights": ins.get("llm_insights"),
    }


@app.get("/dashboard/data", summary="대시보드 데이터 JSON", include_in_schema=False)
def dashboard_data():
    """insights_v3.json + analysis_v2.csv + sample_design.json 종합 JSON."""
    insights_path = _game_file(cfg.APP_ID, "insights_v3.json")
    if not insights_path:
        raise HTTPException(status_code=404, detail="insights_v3.json 없음 — build_insights_v3.py 먼저 실행")

    with open(insights_path, "r", encoding="utf-8") as f:
        ins = json.load(f)
    sd = {}
    sample_path = _game_file(cfg.APP_ID, "sample_design.json")
    if sample_path:
        with open(sample_path, "r", encoding="utf-8") as f:
            sd = json.load(f)

    # ABSA 차트용 데이터 평탄화
    ASPECTS = ["graphics","gameplay","story","performance","value"]
    ASPECT_KR = {"graphics":"그래픽","gameplay":"게임플레이","story":"스토리",
                 "performance":"성능·버그","value":"가격·가성비"}
    aspects_pos, aspects_neu, aspects_neg = [], [], []
    for a in ASPECTS:
        st = ins["aspects"].get(a, {})
        aspects_pos.append(st.get("POSITIVE", 0))
        aspects_neu.append(st.get("NEUTRAL", 0))
        aspects_neg.append(st.get("NEGATIVE", 0))

    EMOTION_KR_REV = {"기쁨":"JOY","만족":"SATISFACTION","분노":"ANGER",
                      "실망":"DISAPPOINTMENT","지루":"BOREDOM","놀람":"SURPRISE","중립":"NEUTRAL"}
    EMOTION_KR = {v:k for k,v in EMOTION_KR_REV.items()}

    pri = ins.get("aspect_priority", [])
    key_findings = []
    if pri:
        w = pri[0]
        key_findings.append({
            "type": "최우선 개선 영역",
            "finding": f"<b>{w['aspect_kr']}</b>의 부정 비율 <b>{w['neg_rate']:.0f}%</b> (언급 {w['mentioned']}회 · 부정 {w['neg']}건)",
            "impact": "한국 유저 비추천의 1순위 사유. QA 예산 1.5~2배 책정 권고",
        })
    emo = ins.get("emotion", {})
    anger, disap, bored = emo.get("ANGER",0), emo.get("DISAPPOINTMENT",0), emo.get("BOREDOM",0)
    if anger >= max(disap, bored) and anger > 0:
        key_findings.append({
            "type": "비추천 유저의 주된 감정",
            "finding": f"가장 빈도 높은 부정 감정: <b>ANGER(분노) {anger}건</b>",
            "impact": "환불·악평 위험. CS 응대 시나리오 + 핫픽스 라인 필수",
        })
    play = ins.get("playtime", {})
    if play:
        worst = min(play.items(), key=lambda x: x[1]["recommend_rate"])
        core = play.get("100h+", {})
        key_findings.append({
            "type": "이탈 위험 구간 (온보딩 핵심)",
            "finding": f"플레이타임 <b>{worst[0]}</b> 구간 추천률 <b>{worst[1]['recommend_rate']:.0f}%</b> (최저), 100h+ 코어층 <b>{core.get('recommend_rate',0):.0f}%</b>",
            "impact": "초기 구간을 못 넘기면 빠르게 이탈. 1주차 온보딩 설계가 성공 변수",
        })

    recs = []
    aspects = ins.get("aspects", {})
    if pri:
        w = pri[0]
        evs = (ins.get("aspect_evidence", {}).get(w["aspect"], {}).get("negative") or [])
        ev = f' 인용: "{evs[0][:50]}"' if evs else ""
        recs.append({"priority":1,
            "action": f"{w['aspect_kr']} 안정성 확보 — QA 예산 1.5~2배",
            "reason": f"비추천 1순위(부정률 {w['neg_rate']:.0f}%). 출시 전 선제적 개선 필요.{ev}"})
    best_a, best_pos = None, 0
    for a, s in aspects.items():
        if s["POSITIVE"] > best_pos: best_pos, best_a = s["POSITIVE"], a
    if best_a:
        recs.append({"priority":2,
            "action": f"{ASPECT_KR.get(best_a, best_a)} 강점을 핵심 경험 축으로 유지",
            "reason": f"한국 유저 호평 최다(POSITIVE {best_pos}건). 축소 시 IP 정체성 손실"})

    n = ins["n_total"]
    pos_pct = ins["n_pos"]/n*100 if n else 0
    worst_kr = pri[0]["aspect_kr"] if pri else ""
    worst_rate = pri[0]["neg_rate"] if pri else 0
    best_kr = ASPECT_KR.get(best_a, "게임플레이") if best_a else "게임플레이"
    exec_summary = (f"한국 유저 추천률 <b>{pos_pct:.0f}%</b>. 핵심 호평은 <b>{best_kr}</b>({best_pos}건), "
                    f"핵심 혹평은 <b>{worst_kr}</b>(부정률 {worst_rate:.0f}%).")

    reviews = []
    analysis_path = _game_file(cfg.APP_ID, "analysis_v2.csv")
    if analysis_path:
        with open(analysis_path, "r", encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                reviews.append({
                    "id": r["recommendationid"],
                    "voted_up": int(r["voted_up"]),
                    "playtime_h": r["playtime_h"],
                    "content": r["content"][:200],
                    "sentiment": r["overall_sentiment"],
                    "emotion": r["emotion"],
                    "key_phrase": r["key_phrase"],
                })

    pop = sd.get("population", {})
    cs = sd.get("current_sample", {})
    rs = sd.get("required_sample_sizes", {})
    sample_design = {
        "pop_total": pop.get("total", 0),
        "required_5pct": rs.get("e_5pct", 0),
        "analyzed": cs.get("analyzed", n),
        "error_pct": cs.get("margin_of_error_analyzed_pct", 0),
    }

    pop_pos_pct = (pop.get("pos_rate", 0) or 0) * 100
    exec_title = (f"Steam 한국 추천률 <b>{pop_pos_pct:.0f}%</b> · "
                  f"수집 데이터 추천률 <b>{pos_pct:.0f}%</b> (비추천 추가 수집 적용)")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "n_total": n, "n_pos": ins["n_pos"], "n_neg": ins["n_neg"],
        "sentiment": ins["sentiment"],
        "emotion": ins["emotion"],
        "emotion_kr": list(EMOTION_KR_REV.keys()),
        "emotion_kr_rev": EMOTION_KR_REV,
        "emotion_pos": ["기쁨","만족","놀람"],
        "emotion_neg": ["분노","실망","지루"],
        "aspects_kr": [ASPECT_KR[a] for a in ASPECTS],
        "aspects_pos": aspects_pos,
        "aspects_neu": aspects_neu,
        "aspects_neg": aspects_neg,
        "playtime": ins["playtime"],
        "priority": ins.get("aspect_priority", []),
        "aspect_evidence": ins.get("aspect_evidence", {}),
        "exec_title": exec_title,
        "exec_summary": exec_summary,
        "key_findings": key_findings,
        "recommendations": recs,
        "sample_design": sample_design,
        "sample_design_full": sd,
        "population": pop,
        "reviews": reviews,
    }


# ====================================================================
# 다운로드 + API 테스트 + 토큰 사용량 (어플리케이션 기능)
# ====================================================================

@app.get("/api/download/{kind}", summary="파일 다운로드", include_in_schema=False)
def download(kind: str):
    mapping = {
        "reviews":  ("reviews.csv",       "text/csv"),
        "analysis": ("analysis_v2.csv",   "text/csv"),
        "insights": ("insights_v4.json",  "application/json"),
        "sample":   ("sample_design.json","application/json"),
        "pdf":      ("팰월드_스팀리뷰_분석서_v3.pdf", "application/pdf"),
    }
    if kind == "charts":
        # 현재 프로젝트의 charts_v4 디렉터리를 ZIP으로 묶어 반환
        import zipfile, io
        charts_dir = cfg.CHARTS_DIR
        if not os.path.isdir(charts_dir):
            raise HTTPException(status_code=404, detail="charts_v4 폴더 없음")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn in os.listdir(charts_dir):
                if fn.lower().endswith(".png"):
                    zf.write(os.path.join(charts_dir, fn), arcname=fn)
        buf.seek(0)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            buf, media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="charts_v4.zip"'},
        )
    if kind not in mapping:
        raise HTTPException(status_code=404, detail="지원하지 않는 종류")
    filename, media = mapping[kind]
    path = cfg.project_file(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{path} 없음")
    return FileResponse(path, media_type=media, filename=os.path.basename(path))


@app.get("/api/usage", summary="토큰 사용량/비용 추정", include_in_schema=False)
def api_usage():
    """analysis_v2.csv 행 수 기반으로 누적 토큰·비용 추정. (Gemini 2.0 Flash 기준)"""
    calls = 0
    if os.path.exists(cfg.ANALYSIS_CSV):
        with open(cfg.ANALYSIS_CSV, "r", encoding="utf-8-sig", newline="") as f:
            calls = sum(1 for _ in csv.DictReader(f))
    # 평균 토큰 추정값
    AVG_INPUT, AVG_OUTPUT = 700, 400
    in_tok = calls * AVG_INPUT
    out_tok = calls * AVG_OUTPUT
    # Gemini 2.0 Flash 가격: $0.10/$0.40 per 1M
    cost = (in_tok * 0.10 + out_tok * 0.40) / 1_000_000
    # 잔액 (가정 — 사용자가 $10 충전, 어림)
    BUDGET = 10.0
    return {
        "calls": calls,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "cost_usd": round(cost, 4),
        "balance_left": round(BUDGET - cost, 4),
        "model": "google/gemini-2.0-flash-001",
        "pricing": {"input_per_1m": 0.10, "output_per_1m": 0.40},
    }


@app.post("/api/test-analyze", summary="단건 분석 테스트 (모델 선택)", include_in_schema=False)
def api_test_analyze(payload: dict):
    """리뷰 텍스트 1건을 선택한 모델로 분석. (API Lab의 시연용)"""
    import httpx
    content = (payload.get("content") or "").strip()
    model   = (payload.get("model") or "google/gemini-2.0-flash-001").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content가 비어 있음")
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or "여기에" in api_key:
        raise HTTPException(status_code=500, detail=".env의 OPENROUTER_API_KEY 미설정")

    system = ("당신은 게임 시장 분석가입니다. 다음 리뷰를 한 번에 분석해서 "
              "JSON으로만 응답: sentiment(긍정/부정/혼합/중립), emotion(JOY/ANGER/...), "
              "keywords(최대 5개), reason(한 줄).")
    user = f'리뷰: "{content[:1000]}"'
    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                "temperature": 0.2, "max_tokens": 500,
                "response_format": {"type": "json_object"},
            },
            timeout=45.0,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:500])
        j = r.json()
        return {
            "model": j.get("model", model),
            "usage": j.get("usage", {}),
            "content": j["choices"][0]["message"]["content"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LLM 인사이트 생성 (토큰 최적화 캐싱)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_insights_prompt(ins: dict, game_name: str) -> str:
    """insights_v4.json → 컴팩트 프롬프트 (~400 토큰). LLM에 raw 리뷰 미전달."""
    ASPECT_KR = {"graphics":"그래픽","gameplay":"게임플레이","story":"스토리",
                 "performance":"성능·버그","value":"가격·가성비"}
    n       = ins.get("n_total", 0)
    pop     = ins.get("population", {})
    pop_pct = round(pop.get("pos_rate", 0) * 100)
    pri     = ins.get("aspect_priority", [])
    ev      = ins.get("aspect_evidence", {})
    emo     = ins.get("emotion", {})
    asp_w   = ins.get("aspects_weighted", {})

    asp_lines = []
    for p in pri[:5]:
        asp_lines.append(f"  {p['aspect_kr']}: 부정률{p['neg_rate']:.0f}%/긍정률{p.get('pos_rate',0):.0f}%")
    asp_table = "\n".join(asp_lines) if asp_lines else "  데이터 없음"

    worst_asp = pri[0]["aspect"] if pri else "performance"
    worst_kr  = pri[0]["aspect_kr"] if pri else "성능"
    neg_quotes = "\n".join(
        f'  - "{q[:50]}"' for q in (ev.get(worst_asp, {}).get("negative") or [])[:3]
    ) or "  없음"

    best_asp = max(ASPECT_KR.keys(), key=lambda a: asp_w.get(a, {}).get("POSITIVE", 0))
    best_kr  = ASPECT_KR.get(best_asp, best_asp)
    pos_quotes = "\n".join(
        f'  - "{q[:50]}"' for q in (ev.get(best_asp, {}).get("positive") or [])[:2]
    ) or "  없음"

    joy_w = round(emo.get("JOY",  {}).get("weighted", 0))
    sat_w = round(emo.get("SATISFACTION", {}).get("weighted", 0))
    ang_w = round(emo.get("ANGER", {}).get("weighted", 0))
    dis_w = round(emo.get("DISAPPOINTMENT", {}).get("weighted", 0))

    return (f"게임: {game_name} | Steam KR {n}건 | Steam추천률 {pop_pct}%\n\n"
            f"영역별 반응(보정후):\n{asp_table}\n\n"
            f"감정(보정후): 기쁨{joy_w}/만족{sat_w}/분노{ang_w}/실망{dis_w}\n\n"
            f"{worst_kr} 부정원문:\n{neg_quotes}\n\n"
            f"{best_kr} 긍정원문:\n{pos_quotes}")


@app.post("/api/generate-insights", summary="LLM 인사이트 생성", include_in_schema=False)
def api_generate_insights(payload: dict):
    """통계 요약만 LLM에 전달 (~400 토큰). 결과는 insights_v4.json에 캐싱."""
    import httpx
    app_id    = str(payload.get("app_id", ""))
    game_name = payload.get("game_name", "Unknown Game")
    force     = payload.get("force", False)
    model     = payload.get("model", "google/gemini-2.0-flash-001")

    ins_path = _game_file(app_id or cfg.APP_ID, "insights_v4.json")
    if not ins_path:
        raise HTTPException(status_code=404, detail="insights_v4.json 없음")

    with open(ins_path, "r", encoding="utf-8") as f:
        ins = json.load(f)

    # 캐시 히트 → LLM 미호출
    if not force and ins.get("llm_insights"):
        return {"cached": True, "insights": ins["llm_insights"]}

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or "여기에" in api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY 미설정")

    system = ("당신은 게임 유저 리뷰 분석 전문가입니다. "
              "통계 데이터를 바탕으로 개발사가 활용할 수 있는 인사이트를 생성하세요. "
              "반드시 JSON만 반환하세요.")
    user = (
        _build_insights_prompt(ins, game_name) +
        "\n\n아래 형식으로만 응답(한국어, 마크다운 금지):\n"
        '{"key_findings":[{"type":"제목(10자이내)","finding":"핵심내용(60자이내)","impact":"시사점(70자이내)"}],'
        '"recommendations":[{"priority":1,"action":"행동지침(30자이내)","reason":"근거(70자이내)"}]}\n'
        "key_findings 3개, recommendations 3개."
    )

    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                  "temperature": 0.3, "max_tokens": 600,
                  "response_format": {"type": "json_object"}},
            timeout=45.0,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:400])
        j       = r.json()
        usage   = j.get("usage", {})
        parsed  = json.loads(j["choices"][0]["message"]["content"])

        ins["llm_insights"] = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model": j.get("model", model),
            "tokens_in":  usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "key_findings":    parsed.get("key_findings", []),
            "recommendations": parsed.get("recommendations", []),
        }
        with open(ins_path, "w", encoding="utf-8") as f:
            json.dump(ins, f, ensure_ascii=False, indent=2)

        return {"cached": False, "insights": ins["llm_insights"], "usage": usage}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/generate-hypothesis", summary="리뷰 기반 기획 인사이트 도출", include_in_schema=False)
async def api_generate_hypothesis(payload: dict):
    """실제 수집된 리뷰 데이터를 기반으로 분야별 기획 인사이트를 도출합니다."""
    app_id    = str(payload.get("app_id", ""))
    game_name = payload.get("game_name", "Unknown Game")
    force     = payload.get("force", False)
    model     = payload.get("model", "google/gemini-2.0-flash-001")

    ins_path = _game_file(app_id or cfg.APP_ID, "insights_v4.json")
    if not ins_path:
        raise HTTPException(status_code=404, detail="insights_v4.json 없음")

    with open(ins_path, "r", encoding="utf-8") as f:
        ins = json.load(f)

    if not force and ins.get("llm_hypothesis"):
        return {"cached": True, "hypothesis": ins["llm_hypothesis"]}

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key or "여기에" in api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY 미설정")

    # ── 신뢰도 기반 분야별 데이터 구축 ──
    ASPECT_LABEL = {
        "graphics":    "그래픽 / 비주얼",
        "gameplay":    "게임플레이 / 전투",
        "story":       "스토리 / 세계관",
        "performance": "성능 / 버그 / 최적화",
        "value":       "가격 / 가성비",
        "multiplayer": "멀티플레이 / 소셜",
    }
    RELIABLE_N = 30  # 신뢰 가능 최소 언급 건수

    priority = ins.get("aspects", {}).get("priority", [])
    evidence = ins.get("aspect_evidence", {})
    pop      = ins.get("population", {})
    pop_pct  = round(pop.get("pos_rate", 0) * 100)
    n_total  = ins.get("n_total", 0)
    phrases_neg = ins.get("top_phrases_neg", [])
    phrases_pos = ins.get("top_phrases_pos", [])
    emo      = ins.get("emotion", {})

    # 신뢰 가능한 분야만 추출
    reliable_aspects = []
    for p in priority:
        asp      = p.get("aspect", "")
        label    = ASPECT_LABEL.get(asp, asp)
        n_total_asp = p.get("mentioned_s", 0)
        n_pos    = p.get("pos_s", 0)
        n_neg    = p.get("neg_s", 0)
        neg_rate = p.get("neg_rate_s", 0)
        pos_rate = 100 - neg_rate

        if n_total_asp < RELIABLE_N:
            continue  # 표본 부족 → 인사이트 생략

        # 원문 인용 (최대 3건)
        ev       = evidence.get(asp, {})
        neg_q    = [q[:60] for q in (ev.get("negative") or [])[:3]]
        pos_q    = [q[:60] for q in (ev.get("positive") or [])[:3]]

        reliable_aspects.append({
            "aspect": label,
            "mentioned": n_total_asp,
            "pos": n_pos,
            "neg": n_neg,
            "pos_rate": round(pos_rate, 1),
            "neg_rate": round(neg_rate, 1),
            "neg_quotes": neg_q,
            "pos_quotes": pos_q,
        })

    # 감정 데이터
    joy_w  = round(emo.get("JOY", {}).get("weighted", 0))
    ang_w  = round(emo.get("ANGER", {}).get("weighted", 0))
    dis_w  = round(emo.get("DISAPPOINTMENT", {}).get("weighted", 0))
    sat_w  = round(emo.get("SATISFACTION", {}).get("weighted", 0))

    # 자주 등장하는 부정/긍정 키워드
    neg_kw = [p[0] if isinstance(p, list) else str(p) for p in phrases_neg[:5]]
    pos_kw = [p[0] if isinstance(p, list) else str(p) for p in phrases_pos[:5]]

    # ── 유용한 리뷰 별도 수집 (Steam API filter=helpful) ──
    # 기존 수집 데이터(랜덤 표본)와 완전히 분리된 추가 수집
    top_helpful_block = ""
    helpful_count = 0
    try:
        helpful_url = (
            f"https://store.steampowered.com/appreviews/{app_id}"
            f"?json=1&filter=helpful&language=koreana&purchase_type=all"
            f"&num_per_page=100&review_type=all"
        )
        # async def 안이므로 반드시 AsyncClient 사용 (동기 httpx.get은 이벤트 루프 블로킹)
        async with httpx.AsyncClient(timeout=20.0) as hclient:
            hr = await hclient.get(helpful_url)
        if hr.status_code == 200:
            hdata = hr.json()
            hreviews = hdata.get("reviews", [])
            top_reviews = []
            for rev in hreviews:
                content = rev.get("review", "")[:300].replace("\n", " ").strip()
                if len(content) < 10:
                    continue
                voted = "긍정" if rev.get("voted_up") else "부정"
                votes_up = rev.get("votes_up", 0)
                playtime_h = rev.get("author", {}).get("playtime_forever", 0) // 60
                label = f"[{voted} | helpful정렬{' ' + str(votes_up) + '표' if votes_up > 0 else ''} | 플레이{playtime_h}h]"
                top_reviews.append(f"{label} {content}")
            helpful_count = len(top_reviews)
            if top_reviews:
                top_helpful_block = (
                    f"=== 추가 수집: 유용한 평가 상위 {helpful_count}건 (Steam filter=helpful, 기존 표본과 독립) ===\n"
                    + "\n".join(f"  • {q}" for q in top_reviews)
                    + "\n\n"
                )
        else:
            print(f"[Steam helpful] status={hr.status_code}")
    except Exception as e:
        print(f"[Steam helpful] 실패: {type(e).__name__}: {e}")
        top_helpful_block = ""


    # LLM 프롬프트 구성 — 원문은 참고용으로만, 출력에는 포함하지 않음
    asp_block = ""
    for a in reliable_aspects:
        asp_block += (
            f"\n【{a['aspect']}】\n"
            f"  통계: 언급 {a['mentioned']}건 | 긍정 {a['pos_rate']}% ({a['pos']}건) / 부정 {a['neg_rate']}% ({a['neg']}건)\n"
        )
        if a["neg_quotes"]:
            # 원문은 "패턴 파악용 참고 자료"로 명시 — 출력에 copy-paste 금지
            asp_block += "  [참고: 부정 원문 패턴 — 출력에 그대로 인용 금지]\n"
            asp_block += "\n".join(f"    • {q}" for q in a["neg_quotes"]) + "\n"
        if a["pos_quotes"]:
            asp_block += "  [참고: 긍정 원문 패턴 — 출력에 그대로 인용 금지]\n"
            asp_block += "\n".join(f"    • {q}" for q in a["pos_quotes"]) + "\n"

    if not asp_block:
        asp_block = "  신뢰 가능한 분야 데이터가 없습니다."

    system = (
        "당신은 10년 경력의 시니어 게임 기획자입니다. "
        "유저 리뷰 데이터를 보고 '왜 이런 반응이 나왔는지'를 게임 장르와 핵심 메카닉 관점에서 분석합니다. "
        "분석은 항상 [장르 → 핵심 메카닉 → 유저 반응 패턴 → 기획적 원인] 의 논리 구조를 따릅니다. "
        "예: 소울라이크 게임에서 구르기(회피) 타이밍과 패링 시스템이 핵심 메카닉이라면, "
        "'답답하다'는 부정 패턴은 입력 딜레이나 스태미나 소모 설계의 문제일 수 있다. "
        "반드시 JSON 포맷만 반환합니다."
    )

    user = (
        f"게임명: {game_name}\n"
        f"수집 리뷰: {n_total}건 | Steam 추천률: {pop_pct}%\n"
        f"감정분포(보정후): 기쁨{joy_w} / 만족{sat_w} / 분노{ang_w} / 실망{dis_w}\n"
        f"주요 부정 키워드 패턴: {', '.join(neg_kw)}\n"
        f"주요 긍정 키워드 패턴: {', '.join(pos_kw)}\n\n"
        f"=== 분야별 리뷰 통계 (신뢰 기준 {RELIABLE_N}건 이상만 포함) ===\n"
        f"{asp_block}\n\n"
        f"{top_helpful_block}"
        "── 분석 지시사항 ──\n"
        "Step 1. 게임명과 리뷰 패턴을 바탕으로 이 게임의 장르와 핵심 메카닉을 먼저 파악하세요.\n"
        "  예: P의 거짓 → 소울라이크 → 핵심 메카닉: 패링/구르기, 보스전, 스태미나\n"
        "  예: 팰월드 → 서바이벌 크래프팅 → 핵심 메카닉: 베이스 건설, 팰 포획, 멀티플레이\n\n"
        "Step 2. 각 분야의 부정/긍정 패턴을 장르·메카닉 맥락에서 해석하여 기획 인사이트를 도출하세요.\n\n"
        "── 출력 규칙 (반드시 준수) ──\n"
        "1. 원문은 '패턴 파악용 참고 자료'이며 출력의 issue 필드에 그대로 인용·나열하지 말 것\n"
        "2. issue 필드: 수치 기반의 깔끔한 분석 문장으로 작성 (예: '게임플레이/전투 169건 부정(17.5%), 난이도·구간 설계 관련 불만 패턴 집중')\n"
        "3. hypothesis 필드: 장르/메카닉 맥락을 명시한 기획적 원인 분석\n"
        "4. design_proposal 필드: 해당 메카닉에 대한 구체적 개선안\n"
        "5. 데이터에 없는 내용(보스명, 버그명, 특정 수치 등)은 절대 지어내지 말 것\n"
        "6. 신뢰 데이터가 있는 모든 분야에 대해 인사이트 작성\n\n"
        "아래 JSON 형식으로만 응답:\n"
        '{"genre": "추론한 게임 장르 (예: 소울라이크 액션 RPG)", '
        '"core_mechanics": ["핵심 메카닉1", "핵심 메카닉2", "핵심 메카닉3"], '
        '"title": "한 줄 핵심 요약 (25자 이내)", '
        '"hypotheses": ['
        '  {"category": "분야명", '
        '   "issue": "수치 기반 깔끔한 관찰 문장", '
        '   "hypothesis": "장르·메카닉 맥락의 기획 원인 분석", '
        '   "design_proposal": "구체적 기획 개선안"}'
        ']}'
    )

    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model,
                  "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                  "temperature": 0.3, "max_tokens": 1500,
                  "response_format": {"type": "json_object"}},
            timeout=60.0,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:400])
        j = r.json()
        parsed = json.loads(j["choices"][0]["message"]["content"])

        ins["llm_hypothesis"] = {
            "title": parsed.get("title", "리뷰 기반 인사이트"),
            "genre": parsed.get("genre", ""),
            "core_mechanics": parsed.get("core_mechanics", []),
            "hypotheses": parsed.get("hypotheses", []),
            "helpful_count": helpful_count,
            "n_total": n_total,
        }
        with open(ins_path, "w", encoding="utf-8") as f:
            json.dump(ins, f, ensure_ascii=False, indent=2)

        return {"cached": False, "hypothesis": ins["llm_hypothesis"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  파이프라인 API — 원클릭 자동화
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from pydantic import BaseModel
from fastapi import BackgroundTasks
from pipeline import run_pipeline

from typing import Optional

class PipelineRunRequest(BaseModel):
    app_id: int
    lang: str = "koreana"
    budget: float = 10.0
    target_error_pct: Optional[float] = None  # 슬라이더가 2.5 같은 소수 오차를 보낸다
    custom_sample_size: Optional[int] = None
    incremental: bool = False

@app.post("/pipeline/run", summary="파이프라인 실행", include_in_schema=False)
def trigger_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks):
    # dynamic registration of the game to games.json
    games = _load_games()
    exists = any(g["app_id"] == request.app_id for g in games)
    if not exists:
        try:
            info = search_steam_game(request.app_id)
            games.append({
                "app_id": request.app_id,
                "name": info["name"],
                "header_image": info["header_image"],
                "type": info["type"],
                "short_description": info["short_description"]
            })
            _save_games(games)
        except Exception:
            games.append({
                "app_id": request.app_id,
                "name": f"App {request.app_id}",
                "header_image": "",
                "type": "game",
                "short_description": ""
            })
            _save_games(games)

    # Trigger background pipeline with incremental option
    background_tasks.add_task(
        run_pipeline,
        app_id=request.app_id,
        lang=request.lang,
        budget=request.budget,
        target_error_pct=request.target_error_pct,
        custom_sample_size=request.custom_sample_size,
        incremental=request.incremental
    )
    return {"status": "started", "message": "파이프라인이 백그라운드에서 실행되었습니다."}


@app.get(
    "/pipeline/estimate",
    summary="비용 사전 견적",
    description="현재 리뷰 데이터 기준 LLM 분석 비용을 미리 계산합니다.",
)
def pipeline_estimate():
    import csv as _csv

    n_reviews = 0
    if os.path.exists(cfg.REVIEWS_CSV):
        with open(cfg.REVIEWS_CSV, "r", encoding="utf-8-sig", newline="") as f:
            for row in _csv.DictReader(f):
                if len((row.get("content") or "").strip()) >= cfg.MIN_REVIEW_LEN:
                    n_reviews += 1

    n_done = 0
    if os.path.exists(cfg.ANALYSIS_CSV):
        with open(cfg.ANALYSIS_CSV, "r", encoding="utf-8-sig", newline="") as f:
            n_done = sum(1 for _ in _csv.DictReader(f))

    n_todo = max(0, n_reviews - n_done)
    estimate = cfg.estimate_cost(n_todo)
    estimate["total_reviews"] = n_reviews
    estimate["already_done"] = n_done
    estimate["to_analyze"] = n_todo
    return estimate


@app.get(
    "/pipeline/config",
    summary="현재 설정 조회",
    description="App ID, 모델, 예산 등 현재 파이프라인 설정을 반환합니다.",
)
def pipeline_config():
    return {
        **cfg.summary(),
        "game_name": cfg.get_game_name(),
        "budget_usd": cfg.BUDGET_USD,
        "reviews_csv_exists": os.path.exists(cfg.REVIEWS_CSV),
        "analysis_csv_exists": os.path.exists(cfg.ANALYSIS_CSV),
        "insights_json_exists": os.path.exists(cfg.INSIGHTS_JSON),
    }


@app.get(
    "/pipeline/result",
    summary="마지막 파이프라인 결과",
    description="가장 최근 파이프라인 실행 결과를 반환합니다.",
)
def pipeline_last_result():
    result_path = cfg.PIPELINE_RESULT
    if not os.path.exists(result_path):
        return {"status": "no_runs", "message": "아직 파이프라인이 실행된 적 없습니다."}
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)

