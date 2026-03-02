@echo off
setlocal
set "APP_URL=http://localhost:5173/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

rem Start backend with venv
start "AGV Backend" cmd /k "cd /d %~dp0backend && call .\venv\Scripts\activate && python -m uvicorn main:app --reload"

rem Start frontend
start "AGV Frontend" cmd /k "cd /d %~dp0frontend\agv-frontend && npm run dev"

rem Open browser after frontend boots
start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started backend and frontend in separate windows, browser will open automatically.
endlocal
