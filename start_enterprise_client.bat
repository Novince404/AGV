@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8010"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "AUTH_READY_URL=http://%AGV_HOST%:%AGV_PORT%/api/v1/auth/me"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if exist "%~dp0VERSION" set /p AGV_VERSION=<"%~dp0VERSION"
if not defined AGV_VERSION set "AGV_VERSION=3.0.0-beta.2"
set "PACKAGE_DIR=%~dp0dist\AGV_Enterprise_Client_%AGV_VERSION%"
set "PACKAGE_LAUNCHER=%PACKAGE_DIR%\start_enterprise_client.bat"

if exist "%~dp0backend.exe" (
  start "AGV Enterprise Client Backend" /D "%~dp0" "%~dp0backend.exe"
) else if exist "%PACKAGE_LAUNCHER%" (
  pushd "%PACKAGE_DIR%"
  call "%PACKAGE_LAUNCHER%"
  set "LAUNCH_EXIT=!errorlevel!"
  popd
  exit /b !LAUNCH_EXIT!
) else (
  echo Enterprise client backend.exe was not found next to this launcher.
  echo Also could not find packaged launcher:
  echo   %PACKAGE_LAUNCHER%
  echo.
  echo Please run build_enterprise_windows_package.bat first, or start the packaged launcher under %PACKAGE_DIR%.
  pause
  exit /b 1
)

echo Waiting for enterprise client API and database readiness on %APP_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; $readyUrl='%APP_URL%health/ready'; $authUrl='%AUTH_READY_URL%'; for ($i=0; $i -lt 40; $i++) { Start-Sleep -Milliseconds 500; try { $ready = Invoke-WebRequest -Uri $readyUrl -UseBasicParsing -TimeoutSec 2; $auth = Invoke-WebRequest -Uri $authUrl -UseBasicParsing -TimeoutSec 2; if ($ready.StatusCode -eq 200 -and $auth.StatusCode -eq 200) { $ok=$true; break } } catch {} }; if ($ok) { exit 0 } else { Write-Host 'Enterprise client API did not become ready in time.'; exit 1 }"
if errorlevel 1 (
  echo Enterprise client backend or API did not become ready. Please check the backend window for logs.
  exit /b 1
)

if exist "%~dp0backend.exe" start "AGV Enterprise Scheduler" /D "%~dp0" "%~dp0backend.exe" --scheduler

if exist "%CHROME_EXE%" (
  start "AGV Browser" "%CHROME_EXE%" "%APP_URL%"
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
  start "AGV Browser" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%APP_URL%"
) else (
  start "AGV Browser" "%APP_URL%"
)

echo Started AGV enterprise API and scheduler package processes.
endlocal
