@echo off
cd /d "%~dp0"
echo =================================================================
echo   Executing Local CI/CD Pipeline for AI Image Search Project
echo =================================================================
python run_ci_pipeline.py
pause
