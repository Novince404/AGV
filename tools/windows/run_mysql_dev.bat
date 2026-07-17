@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

if not exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
  echo ERROR: backend venv not found: %BACKEND_DIR%\venv
  exit /b 1
)

echo This launcher expects a configured MySQL URL in backend\.env or the current environment.
echo Run "python agv.py database upgrade --backup-confirmed" from backend first.
set "AGV_DATA_BACKEND=mysql"
set "AGV_DATABASE_AUTO_CREATE=false"
set "AGV_SCHEDULER_V3_ENABLED=false"
start "AGV MySQL API" "%ComSpec%" /k call "%PROJECT_ROOT%\tools\windows\run_mysql_backend_supervised.bat"

set "AGV_SCHEDULER_V3_ENABLED=true"
start "AGV MySQL Scheduler" cmd /k "cd /d %BACKEND_DIR% && call .\venv\Scripts\activate.bat && set AGV_DATA_BACKEND=mysql && set AGV_DATABASE_AUTO_CREATE=false && set AGV_SCHEDULER_V3_ENABLED=true && python scheduler_main.py"

echo Started MySQL API supervisor and scheduler in separate windows.
endlocal
