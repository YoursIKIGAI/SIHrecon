@echo off
title Metro Flood Nowcast System Launcher
echo Starting Urban Flood Prediction & Routing System...
start "Backend Server" cmd /k "start_backend.bat"
timeout /t 3 /nobreak > nul
start "Frontend Dashboard" cmd /k "start_frontend.bat"
echo System launching!
echo Backend will be ready on:  http://localhost:8000/docs
echo Frontend will be ready on: http://localhost:3000
