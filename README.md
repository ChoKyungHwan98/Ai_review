# 🎮 Steam Review Analytics — AI 리뷰 분석 시스템

Steam 게임 리뷰를 자동 수집 → LLM 다차원 분석 → 편향 보정 → 대시보드 시각화까지
**원클릭으로 실행**하는 리뷰 인텔리전스 시스템입니다.

## ✨ 핵심 기능

| 기능 | 설명 |
|---|---|
| **자동 수집** | Steam API에서 한국어 리뷰를 층화 추출 (Cochran 표본 설계) |
| **LLM 분석** | 감성 + 감정 + ABSA 6축 + 모바일 이식 시사점 다차원 분석 |
| **편향 보정** | 가중치 보정(post-stratification)으로 표본 편향 복원 |
| **품질 점검** | 4축 품질 점수 (완전성·일관성·대표성·정확도) |
| **신뢰도 검증** | 30건 표본 검증 + 4사분면 신뢰도 매트릭스 |
| **대시보드** | 9개 탭 인터랙티브 대시보드 (FastAPI 기반) |
| **비용 통제** | LLM 비용 사전 견적 + 예산 초과 시 자동 중단 |

## 🚀 빠른 시작

### 1. 설치
```bash
git clone <repo>
cd 프로그램
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. 환경 설정
```bash
cp .env.example .env
# .env 파일을 열어 OPENROUTER_API_KEY를 입력하세요
# 다른 게임을 분석하려면 APP_ID를 변경하세요
```

### 3. 실행 방법

#### 방법 A: 원클릭 파이프라인 (권장)
```bash
# 기본 (팰월드, 한국어)
python pipeline.py

# 다른 게임
python pipeline.py --app-id 730 --lang english    # CS2
python pipeline.py --app-id 570 --lang koreana    # Dota 2

# 예산 한도 지정
python pipeline.py --budget 2.0
```

#### 방법 B: 대시보드 실행
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8765
# → http://127.0.0.1:8765/dashboard
```

#### 방법 C: 개별 스크립트 실행
```bash
python collect_reviews_v2.py    # ① 리뷰 수집
python analyze_reviews_v2.py    # ② LLM 분석
python quality_check.py         # ③ 품질 점검
python verify_analysis.py       # ④ 신뢰도 검증
python build_insights_v4.py     # ⑤ 인사이트 생성
```

## 📊 API 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/` | 헬스체크 |
| GET | `/dashboard` | 대시보드 UI |
| GET | `/dashboard/data/v4` | 대시보드 전체 데이터 (JSON) |
| GET | `/reviews` | 리뷰 목록 |
| GET | `/stats` | 통계 요약 |
| POST | `/analyze` | 단건 리뷰 분석 |
| GET | `/pipeline/estimate` | 비용 사전 견적 |
| GET | `/pipeline/config` | 현재 설정 조회 |
| GET | `/pipeline/result` | 마지막 실행 결과 |
| GET | `/docs` | OpenAPI 문서 (Swagger) |

## 🏗️ 프로젝트 구조

```
AI 리뷰데이터 분석/
├── 프로그램/                # 실행 코드·정적 UI·의존성
│   ├── config.py            # 중앙 설정 (APP_ID, MODEL, 예산 등)
│   ├── pipeline.py          # 원클릭 자동화 파이프라인
│   ├── main.py              # FastAPI 서버 + 대시보드
│   ├── database.py          # SQLite DB 접근 계층
│   ├── models.py             # Pydantic 스키마
│   ├── analyzer.py           # 단건 LLM 분석 (API용)
│   │
│   ├── collect_reviews_v2.py
│   ├── analyze_reviews_v2.py
│   ├── quality_check.py
│   ├── verify_analysis.py
│   ├── build_insights_v4.py
│   ├── sample_design.py
│   ├── static/               # 대시보드 프론트엔드
│   └── _archive/             # 이전 버전 파일 (참조용)
└── 프로젝트/                # 단일 저장소: 게임별 폴더
    ├── games.json
    ├── review_analysis.db
    └── <Steam App ID>/       # reviews.csv, analysis_v2.csv, JSON, charts_v4/
```

이 도구는 다른 게임기획 도구와 동일하게 `프로그램`과 `프로젝트`를 분리합니다. 모든 CSV·JSON·차트·파이프라인 결과는 상위 `프로젝트\<Steam App ID>` 아래의 단일 저장소에만 생성되며, 기존 `data` 폴더나 실행 위치 기준 fallback은 사용하지 않습니다.

## ⚙️ 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENROUTER_API_KEY` | (필수) | OpenRouter API 키 |
| `APP_ID` | `1623730` | Steam 게임 App ID |
| `LANG_CODE` | `koreana` | 리뷰 언어 |
| `MODEL` | `google/gemini-2.0-flash-001` | LLM 모델 |
| `BUDGET_USD` | `5.0` | LLM 분석 예산 한도 (USD) |
| `TARGET_ERROR_PCT` | `5` | 목표 오차한계 (%) |
| `MIN_NEG_REVIEWS` | `100` | 부정 리뷰 최소 수집 목표 |

## 📈 분석 결과 예시 (팰월드)

- **수집**: 한국어 리뷰 750건 (모집단 21,727건 중)
- **분석**: 487건 LLM 다차원 분석 완료 (비용 약 $0.06)
- **품질**: 종합 84.9점 / PASS
- **신뢰도**: 관대 기준 86.7% (엄격 40%, MIXED/NEUTRAL 보수적 판정 포함)
- **보정**: Steam 추천률 95% → 표본 67% → **보정 후 95% 일치**

## 📜 라이선스 및 출처

- **Steam 리뷰 데이터**: Valve Steam Web API (공개 API, 비상업적 분석)
- **LLM 분석**: OpenRouter API (Google Gemini 2.0 Flash)
- 본 프로젝트는 교육·포트폴리오 목적으로 제작되었습니다.
