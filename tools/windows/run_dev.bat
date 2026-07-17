@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "APP_URL=http://localhost:5173/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

rem Memory mode cannot share state between processes, so this convenience
rem launcher hosts the scheduler in the API process. Use run_sqlite_dev.bat
rem when validating the v3 split-process runtime.
start "AGV Backend" cmd /k "cd /d %PROJECT_ROOT%\backend && call .\venv\Scripts\activate && set AGV_SCHEDULER_V3_ENABLED=true && python -m uvicorn main:app --reload"

rem Start frontend
start "AGV Frontend" cmd /k "cd /d %PROJECT_ROOT%\frontend && npm run dev"

rem Open browser after frontend boots
start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started frontend and API. The API also hosts the scheduler for memory-mode convenience.
endlocal
