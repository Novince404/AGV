@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

if "%AGV_HOST%"=="" set "AGV_HOST=127.0.0.1"
if "%AGV_PORT%"=="" set "AGV_PORT=8010"
if "%AGV_BACKEND_RESTART_DELAY_SEC%"=="" set "AGV_BACKEND_RESTART_DELAY_SEC=3"
if "%AGV_BACKEND_MAX_RESTARTS%"=="" set "AGV_BACKEND_MAX_RESTARTS=0"
if "%AGV_DATABASE_AUTO_CREATE%"=="" set "AGV_DATABASE_AUTO_CREATE=true"

set "AGV_DATA_BACKEND=mysql"
rem This launcher owns the API only. Start run_mysql_dev.bat for the matching
rem scheduler worker, or use the Docker Compose trial stack.
set "AGV_SCHEDULER_V3_ENABLED=false"
set "LOG_DIR=%BACKEND_DIR%\logs"
set "SUPERVISOR_LOG=%LOG_DIR%\backend_supervisor.log"

if not exist "%BACKEND_DIR%\venv\Scripts\activate.bat" (
  echo ERROR: backend venv not found: %BACKEND_DIR%\venv
  exit /b 1
)

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set /a RESTART_COUNT=0

:restart_backend
set /a RESTART_COUNT+=1
call :timestamp STARTED_AT
echo [%STARTED_AT%] Starting AGV backend MySQL on http://%AGV_HOST%:%AGV_PORT%/ ^(attempt %RESTART_COUNT%^)
echo [%STARTED_AT%] starting backend attempt %RESTART_COUNT% on %AGV_HOST%:%AGV_PORT% >> "%SUPERVISOR_LOG%"

pushd "%BACKEND_DIR%"
call "%BACKEND_DIR%\venv\Scripts\activate.bat"
python -m uvicorn main:app --host %AGV_HOST% --port %AGV_PORT% --log-level info
set "EXIT_CODE=!ERRORLEVEL!"
popd

call :timestamp STOPPED_AT
echo [%STOPPED_AT%] Backend process exited with code !EXIT_CODE!.
echo [%STOPPED_AT%] backend exited with code !EXIT_CODE! >> "%SUPERVISOR_LOG%"

if not "%AGV_BACKEND_MAX_RESTARTS%"=="0" (
  if !RESTART_COUNT! GEQ %AGV_BACKEND_MAX_RESTARTS% (
    echo Reached AGV_BACKEND_MAX_RESTARTS=%AGV_BACKEND_MAX_RESTARTS%; supervisor stopped.
    exit /b !EXIT_CODE!
  )
)

echo Restarting backend in %AGV_BACKEND_RESTART_DELAY_SEC% seconds. Press Ctrl+C to stop.
timeout /t %AGV_BACKEND_RESTART_DELAY_SEC% /nobreak > nul
goto restart_backend

:timestamp
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set "%~1=%%A"
exit /b 0
