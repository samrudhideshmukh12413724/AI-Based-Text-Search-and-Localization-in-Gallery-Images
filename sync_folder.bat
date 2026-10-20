@echo off
title DocuLens AI - Instant Folder Sync
color 0b
echo ========================================================
echo       DOCULENS AI - FOLDER SYNC & BATCH INDEXER
echo ========================================================
echo.

set FOLDER_PATH=%~1

if "%FOLDER_PATH%"=="" (
    echo [TIP] You can also drag and drop any folder directly onto this .bat file!
    echo.
    set /p FOLDER_PATH="Enter the path to your image/document folder (or press Enter for test_images): "
)

if "%FOLDER_PATH%"=="" (
    set FOLDER_PATH=%~dp0test_images
)

:: Strip surrounding quotes if present
set FOLDER_PATH=%FOLDER_PATH:"=%

echo.
echo [*] Target Folder: %FOLDER_PATH%
echo [*] Checking Backend connection on http://127.0.0.1:8000...

python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3); print('[+] Backend is online!')" 2>nul
if %errorlevel% neq 0 (
    echo [!] Backend server is not running on port 8000.
    echo [*] Starting FastAPI Backend Server in a new window...
    start "DocuLens AI - Backend Server" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    timeout /t 5 /nobreak >nul
)

echo.
echo [*] Syncing all photos and documents from folder into DocuLens AI...
echo ========================================================
python "%~dp0upload_my_images.py" "%FOLDER_PATH%"
echo ========================================================
echo.
echo [OK] Folder sync process completed!
echo.
pause
