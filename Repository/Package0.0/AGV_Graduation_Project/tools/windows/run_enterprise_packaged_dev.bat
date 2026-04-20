@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8010"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "AUTH_READY_URL=http://%AGV_HOST%:%AGV_PORT%/auth/me"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "SQLITE_DB=sqlite:///../data/agv_dispatch.db"

call "%PROJECT_ROOT%\build_frontend_dist_enterprise.bat"
if errorlevel 1 exit /b 1

if not exist "%PROJECT_ROOT%\data" mkdir "%PROJECT_ROOT%\data"
if exist "%PROJECT_ROOT%\backend\.env" (
  start "AGV Enterprise Client Backend" cmd /k "cd /d %PROJECT_ROOT%\backend && call .\venv\Scripts\activate && set AGV_SERVE_FRONTEND_DIST=true && set AGV_FRONTEND_DIST_DIR=%PROJECT_ROOT%\frontend\agv-frontend\dist-enterprise && set AGV_APP_TITLE=AGV Enterprise Client Backend && set AGV_ROOT_MESSAGE=AGV Enterprise Client Backend started && set AGV_HOST=%AGV_HOST% && set AGV_PORT=%AGV_PORT% && python -m uvicorn main:app --host %AGV_HOST% --port %AGV_PORT%"
) else (
  start "AGV Enterprise Client Backend" cmd /k "cd /d %PROJECT_ROOT%\backend && call .\venv\Scripts\activate && set AGV_DATA_BACKEND=sqlite && set AGV_DATABASE_URL=%SQLITE_DB% && set AGV_DATABASE_AUTO_CREATE=true && set AGV_SERVE_FRONTEND_DIST=true && set AGV_FRONTEND_DIST_DIR=%PROJECT_ROOT%\frontend\agv-frontend\dist-enterprise && set AGV_APP_TITLE=AGV Enterprise Client Backend && set AGV_ROOT_MESSAGE=AGV Enterprise Client Backend started && set AGV_HOST=%AGV_HOST% && set AGV_PORT=%AGV_PORT% && python -m uvicorn main:app --host %AGV_HOST% --port %AGV_PORT%"
)

echo Waiting for enterprise package-like local mode to finish API startup on %APP_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$ok=$false; $appUrl='%APP_URL%'; $authUrl='%AUTH_READY_URL%'; for ($i=0; $i -lt 40; $i++) { Start-Sleep -Milliseconds 500; try { $app = Invoke-WebRequest -Uri $appUrl -UseBasicParsing -TimeoutSec 2; $auth = Invoke-WebRequest -Uri $authUrl -UseBasicParsing -TimeoutSec 2; if ($app.StatusCode -eq 200 -and $auth.StatusCode -eq 200) { $ok=$true; break } } catch {} }; if ($ok) { if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' $appUrl } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' $appUrl } else { Start-Process $appUrl }; exit 0 } else { Write-Host 'Enterprise package-like local mode backend or API did not become ready in time.'; exit 1 }"
if errorlevel 1 (
  echo Enterprise package-like local mode backend or API did not become ready. Please check the backend window for logs.
  exit /b 1
)

echo Started enterprise package-like local mode on %APP_URL%
endlocal
