@echo off
title AI Image Search - Run on Chrome (Instant Demo)

echo ========================================================
echo      AI IMAGE SEARCH - INSTANT DEMO RUNNER (CHROME)
echo ========================================================
echo.

:: Add Flutter to PATH
set PATH=%PATH%;C:\src\flutter\bin

:: 1. Start Python Backend in a separate window
echo [1/2] Starting FastAPI Backend Server...
start "AI Image Search - Backend Server" cmd /k "cd /d "%~dp0backend" && echo Starting Backend... && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 2. Launch Flutter App on Chrome
echo.
echo [2/2] Launching Flutter Mobile App on Chrome...
echo ========================================================
echo TIP: Once Chrome opens, press F12 and click the Phone
echo icon (Ctrl+Shift+M) to view it in Mobile Phone mode!
echo ========================================================
echo.
cd /d "%~dp0mobile_app"
call flutter run -d chrome

pause
