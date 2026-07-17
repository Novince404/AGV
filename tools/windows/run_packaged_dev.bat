@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8000"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "SQLITE_DB=sqlite:///../data/agv_dispatch.db"

call "%PROJECT_ROOT%\build_frontend_dist.bat"
if errorlevel 1 exit /b 1

if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if not exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
  echo ERROR: backend venv not found: %BACKEND_DIR%\venv
  exit /b 1
)

rem Apply migrations once before starting the independent API and scheduler.
pushd "%BACKEND_DIR%"
call .\venv\Scripts\activate.bat
set "AGV_APP_ENV=demo"
set "AGV_DATA_BACKEND=sqlite"
set "AGV_DATABASE_URL=%SQLITE_DB%"
set "AGV_DATABASE_AUTO_CREATE=false"
python agv.py database upgrade
if errorlevel 1 (
  echo SQLite database upgrade failed; packaged demo was not started.
  popd
  exit /b 1
)
popd

start "AGV Packaged API" cmd /k "cd /d %BACKEND_DIR% && call .\venv\Scripts\activate.bat && set AGV_APP_ENV=demo && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=false && set AGV_SCHEDULER_V3_ENABLED=false && set AGV_SERVE_FRONTEND_DIST=true && set AGV_FRONTEND_DIST_DIR=%PROJECT_ROOT%\frontend\dist && set AGV_HOST=%AGV_HOST% && set AGV_PORT=%AGV_PORT% && python -m uvicorn main:app --host %AGV_HOST% --port %AGV_PORT%"
start "AGV Packaged Scheduler" cmd /k "cd /d %BACKEND_DIR% && call .\venv\Scripts\activate.bat && set AGV_APP_ENV=demo && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=false && set AGV_SCHEDULER_V3_ENABLED=true && python scheduler_main.py"

start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started package-like local demo API and scheduler on %APP_URL%
endlocal
