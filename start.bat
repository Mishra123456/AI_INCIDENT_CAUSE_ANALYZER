@echo off
echo ============================================
echo   Sentinel AI — Incident Root Cause Analyzer
echo ============================================
echo.

REM Check if venv exists, create if not
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Sentinel AI server...
echo Open http://localhost:8000 in your browser
echo.
python run.py
