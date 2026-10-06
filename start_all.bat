@echo off
cd /d "%~dp0"
echo Starting backend + frontend in separate windows...
start "TeacherAI-Backend" cmd /k start_backend.bat
timeout /t 2 >nul
start "TeacherAI-Frontend" cmd /k start_frontend.bat
