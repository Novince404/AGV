@echo off
setlocal

set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8000"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

if exist "%~dp0backend.exe" (
  start "AGV Backend Package" "%~dp0backend.exe"
) else (
  call "%~dp0tools\windows\run_packaged_dev.bat"
  exit /b %errorlevel%
)

echo Waiting for API and database readiness on %APP_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for ($i=0; $i -lt 40; $i++) { Start-Sleep -Milliseconds 500; try { $res = Invoke-WebRequest -Uri '%APP_URL%health/ready' -UseBasicParsing -TimeoutSec 2; if ($res.StatusCode -eq 200) { $ok=$true; break } } catch {} }; if ($ok) { exit 0 } else { Write-Host 'API did not become ready in time.'; exit 1 }"
if errorlevel 1 (
  echo API did not become ready. Please check the AGV Backend Package window for logs.
  exit /b 1
)

rem The API has finished its first-run migration.  Start the independent
rem deterministic scheduler only now so both processes never migrate SQLite
rem concurrently.
if exist "%~dp0backend.exe" start "AGV Scheduler Package" /D "%~dp0" "%~dp0backend.exe" --scheduler

if exist "%CHROME_EXE%" (
  start "AGV Browser" "%CHROME_EXE%" "%APP_URL%"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  start "AGV Browser" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%APP_URL%"
) else (
  start "AGV Browser" "%APP_URL%"
)

echo Started AGV API and scheduler package processes.
endlocal
