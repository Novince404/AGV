@echo off
setlocal

set "APP_URL=http://127.0.0.1:8000/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "SQLITE_DB=sqlite:///../data/agv_dispatch.db"

call "%~dp0build_frontend_dist.bat"
if errorlevel 1 exit /b 1

if not exist "%~dp0data" mkdir "%~dp0data"

start "AGV Packaged Backend" cmd /k "cd /d %~dp0backend && call .\venv\Scripts\activate && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=true && set AGV_SERVE_FRONTEND_DIST=true && set AGV_FRONTEND_DIST_DIR=%~dp0frontend\agv-frontend\dist && python -m uvicorn main:app"

start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started package-like local demo mode on %APP_URL%
endlocal
