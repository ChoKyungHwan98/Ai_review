# AI 리뷰데이터 분석기

Steam 리뷰를 표본 수집하고 OpenRouter 모델로 분류해, 게임기획자가 **전체 반응 → 핵심 주제 → 플레이 구간 → 실제 원문** 순서로 확인하는 로컬 분석 도구입니다.

## 현재 구조

```text
Steam 리뷰 API
  → 표본 설계·수집
  → v3 리뷰 분류
     A. 게임별 주제 발견
     B. 전체 리뷰 반응·주제·재미 분류
     C. 불만 리뷰만 문제·원인·요청 심층 분석
  → 품질 점검·표본 검증
  → v5 인사이트 집계
  → 대시보드와 근거 원문
```

분석 결과 화면은 특정 게임에 맞춘 고정 문구를 사용하지 않습니다. Steam 게임 정보와 분석 파일을 기준으로 같은 구조를 모든 게임에 적용합니다.

## 주요 기능

- Steam App ID와 언어를 지정한 리뷰 수집
- 목표 오차와 최소 비추천 리뷰 수를 반영한 표본 설계
- 게임마다 반복되는 주제를 먼저 찾는 동적 주제 분류
- 긍정·부정·혼합·판단 어려움의 반응 분류
- 8가지 재미 유형과 주제별 긍정·부정 언급 집계
- 불만 리뷰에 한정한 문제·원인·사용자 요청 분리
- 플레이 시간별 비추천 비율과 작은 표본 경고
- 주제별 실제 리뷰 원문 확인
- OpenRouter 모델 목록·가격 조회와 무료/유료 구분
- 실행 전 예상 비용, 실행 중 예산 예약, 한도 초과 중단

## 토큰 사용 최적화

1. 짧고 정보가 적은 리뷰는 LLM 호출 전에 걸러냅니다.
2. 주제는 최대 150건에서 한 번 발견하고 전체 리뷰에 재사용합니다.
3. 전체 분류는 15건씩 묶고 짧은 키의 JSON으로 응답받습니다. 본문이 같은 리뷰는 한 번만 보냅니다.
4. 불만 심층 분석은 불만 가능성이 있는 리뷰에만 실행합니다.
5. v5 요약은 원문 전체가 아닌 집계 결과를 한 번만 전달합니다.
6. JSONL 결과를 이어 쓰므로 완료한 리뷰는 재실행하지 않습니다.
7. 모델별 실제 단가로 남은 작업 비용을 계산하고 예산을 예약합니다.
8. 요약 캐시는 입력 해시가 같으면 재사용합니다.

무료 모델과 유료 모델은 같은 출력 계약을 사용합니다. 모델의 JSON 형식 지원 여부와 문맥 길이는 실행 전에 확인하며, 결과 누락 시 해당 묶음만 다시 시도합니다.

## 설치

```powershell
git clone https://github.com/ChoKyungHwan98/Ai_review.git
cd Ai_review
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 `OPENROUTER_API_KEY`를 입력합니다.

## 실행

```powershell
# 대시보드
python -m uvicorn main:app --host 127.0.0.1 --port 8765

# 전체 파이프라인
python pipeline.py --app-id 1623730 --lang koreana --budget 5

# 단계별 실행
python collect_reviews.py
python analyze_reviews_v3.py
python quality_check.py
python verify_analysis.py
python build_insights_v5.py
```

대시보드: `http://127.0.0.1:8765/dashboard`

## 환경 변수

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | 필수 | OpenRouter 키 |
| `APP_ID` | `1623730` | 기본 Steam App ID |
| `LANG_CODE` | `koreana` | Steam 리뷰 언어 |
| `MODEL` | `google/gemini-2.5-flash-lite` | 분석 모델 |
| `BUDGET_USD` | `5.0` | 실행당 최대 분석 예산 |
| `TARGET_ERROR_PCT` | `5` | 목표 오차 범위 |
| `MIN_NEG_REVIEWS` | `100` | 비추천 리뷰 최소 목표 |
| `MIN_REVIEW_LEN` | `8` | AI 분석 최소 글자 수 |

## 결과 파일

게임별 파일은 소스 저장소 밖의 형제 폴더 `../프로젝트/<Steam App ID>/`에 저장됩니다.

| 파일 | 내용 |
| --- | --- |
| `reviews.csv` | Steam 원본 리뷰 |
| `sample_design.json` | 모집단과 표본 설계 |
| `themes_v3.json` | 게임별 주제 목록 |
| `analysis_v3.jsonl` | 리뷰별 반응·재미·주제 분류 |
| `analysis_v3.csv` | 품질 점검과 리뷰 탐색용 표 |
| `complaints_v3.jsonl` | 불만의 문제·원인·요청 |
| `usage_v3.json` | 단계별 호출·토큰·모델 단가 |
| `quality_report.json` | 데이터 품질 점검 |
| `verify_report.json` | 표본 검증 결과 |
| `insights_v5.json` | 대시보드 집계와 요약 |
| `pipeline_result.json` | 실행 상태와 단계별 결과 |

## 주요 API

| 방식 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/dashboard` | 대시보드 |
| `GET` | `/dashboard/data/v5` | 현재 분석 결과 |
| `GET` | `/dashboard/evidence` | 선택 주제의 근거 리뷰 |
| `GET` | `/api/games` | 분석이 완료된 게임 목록 |
| `GET` | `/api/models` | 선택 가능한 OpenRouter 모델 |
| `POST` | `/pipeline/run` | 분석 시작 |
| `GET` | `/pipeline/estimate` | 남은 작업 비용 견적 |
| `GET` | `/pipeline/result` | 최근 실행 상태 |
| `GET` | `/api/usage` | 토큰과 비용 기록 |

## 폴더 구성

```text
.
├── main.py                    # FastAPI 서버
├── config.py                  # 경로·모델·예산 설정
├── pipeline.py                # 전체 실행 흐름
├── collect_reviews.py         # Steam 수집과 표본 설계
├── analyze_reviews_v3.py      # 주제·반응·재미·불만 분석
├── build_insights_v5.py       # 화면용 집계와 요약
├── dashboard_evidence.py      # 근거 원문 조회
├── model_catalog.py           # OpenRouter 모델과 가격
├── budget_control.py          # 실행 중 예산 통제
├── token_budget.py            # 실행 전 비용 견적
├── quality_check.py           # 품질 점검
├── verify_analysis.py         # 표본 검증
├── static/                    # 대시보드 화면
├── tests/                     # 핵심 회귀 검사
└── docs/                      # 구조·조사·화면 설계 문서
```

## 화면 설계와 Impeccable

대시보드는 결론을 먼저 보여주고, 차트와 실제 리뷰로 근거를 확인하는 구조를 사용합니다. Impeccable 4.3.1은 개발자의 개인 Codex 스킬로 설치되어 UI 점검에 사용합니다. 실행 프로그램의 의존성이 아니므로 저장소에 복제하거나 `requirements.txt`에 추가하지 않습니다.

자세한 설명은 [포트폴리오용 제품 설계서](docs/포트폴리오용_제품_설계서.md), [파이프라인 구조](docs/파이프라인_구조.md), [리뷰 진단 시각화 설계](docs/리뷰진단_시각화_설계.md)를 참고하세요.
