@echo off
setlocal

set "APP_URL=http://localhost:5173/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "SQLITE_DB=sqlite:///./agv_dispatch.db"

rem Start backend with sqlite backend
start "AGV Backend SQLite" cmd /k "cd /d %~dp0backend && call .\venv\Scripts\activate && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=true && python -m uvicorn main:app --reload"

rem Start frontend
start "AGV Frontend" cmd /k "cd /d %~dp0frontend\agv-frontend && npm run dev"

rem Open browser after frontend boots
start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started backend and frontend in SQLite mode, browser will open automatically.
endlocal
