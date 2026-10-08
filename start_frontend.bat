@echo off
title Metro Flood Frontend (React + Vite)
echo ========================================================
echo [1/2] Installing frontend dependencies...
echo ========================================================
cd frontend
call npm install

echo ========================================================
echo [2/2] Launching Vite development server on port 3000...
echo ========================================================
call npm run dev
pause
