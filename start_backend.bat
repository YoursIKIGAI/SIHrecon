@echo off
title Metro Flood Backend (FastAPI)
echo ========================================================
echo [1/2] Installing backend dependencies...
echo ========================================================
pip install -r backend\requirements.txt

echo ========================================================
echo [2/2] Launching FastAPI backend server on port 8000...
echo ========================================================
python run_demo.py
pause
