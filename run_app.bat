@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
echo =========================================
echo  AI 리뷰데이터 분석 서버
echo =========================================
echo.
echo 서버를 시작합니다... (이 창을 닫으면 서버가 종료됩니다)
echo.

set "PYTHON=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8765
popd
endlocal
