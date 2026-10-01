@echo off
cd /d "%~dp0backend"
echo Starting AI Image Search backend on http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
