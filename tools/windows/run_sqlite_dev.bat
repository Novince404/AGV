@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "APP_URL=http://localhost:5173/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "SQLITE_DB=sqlite:///./agv_dispatch.db"

if not exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
  echo ERROR: backend venv not found: %BACKEND_DIR%\venv
  exit /b 1
)

rem Migrate before either runtime starts.  This prevents two first-run
rem processes from competing over SQLite schema creation.
pushd "%BACKEND_DIR%"
call .\venv\Scripts\activate.bat
set "AGV_APP_ENV=demo"
set "AGV_DATA_BACKEND=sqlite"
set "AGV_DATABASE_URL=%SQLITE_DB%"
set "AGV_DATABASE_AUTO_CREATE=false"
python agv.py database upgrade
if errorlevel 1 (
  echo SQLite database upgrade failed; API and scheduler were not started.
  popd
  exit /b 1
)
popd

rem API and scheduler intentionally use separate processes.  The scheduler
rem owns the durable lease and is the only process that advances simulation.
start "AGV API SQLite" cmd /k "cd /d %BACKEND_DIR% && call .\venv\Scripts\activate.bat && set AGV_APP_ENV=demo && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=false && set AGV_SCHEDULER_V3_ENABLED=false && python -m uvicorn main:app --reload"
start "AGV Scheduler SQLite" cmd /k "cd /d %BACKEND_DIR% && call .\venv\Scripts\activate.bat && set AGV_APP_ENV=demo && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=false && set AGV_SCHEDULER_V3_ENABLED=true && python scheduler_main.py"

rem Open browser after frontend boots
start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started SQLite API, scheduler, and frontend in separate windows.
endlocal
