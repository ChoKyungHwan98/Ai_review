"""main.py에 CSV 다운로드 API 추가"""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

FILE = os.path.join(os.path.dirname(__file__), 'main.py')

with open(FILE, encoding='utf-8') as f:
    content = f.read()

# review_population_stats 함수 끝 뒤에 CSV 다운로드 API 추가
CSV_API = '''

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

'''

# review_population_stats 함수 끝 찾기
marker = '@app.get("/dashboard/data/v4"'
if marker in content:
    content = content.replace(marker, CSV_API + marker)
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK: added /api/reviews/download and /api/analysis/download')
else:
    print('ERROR: marker not found')
