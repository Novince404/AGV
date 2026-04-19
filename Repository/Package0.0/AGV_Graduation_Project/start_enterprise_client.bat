@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8010"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "AUTH_READY_URL=http://%AGV_HOST%:%AGV_PORT%/auth/me"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "PACKAGE_LAUNCHER=%~dp0dist\AGV_Enterprise_Client_v1\start_enterprise_client.bat"

if exist "%~dp0backend.exe" (
  start "AGV Enterprise Client Backend" /D "%~dp0" "%~dp0backend.exe"
) else if exist "%PACKAGE_LAUNCHER%" (
  pushd "%~dp0dist\AGV_Enterprise_Client_v1"
  call "%PACKAGE_LAUNCHER%"
  set "LAUNCH_EXIT=!errorlevel!"
  popd
  exit /b !LAUNCH_EXIT!
) else (
  echo Enterprise client backend.exe was not found next to this launcher.
  echo Also could not find packaged launcher:
  echo   %PACKAGE_LAUNCHER%
  echo.
  echo Please run build_enterprise_windows_package.bat first, or start the packaged launcher under dist\AGV_Enterprise_Client_v1.
  pause
  exit /b 1
)

echo Waiting for enterprise client backend and API on %APP_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; $appUrl='%APP_URL%'; $authUrl='%AUTH_READY_URL%'; for ($i=0; $i -lt 40; $i++) { Start-Sleep -Milliseconds 500; try { $app = Invoke-WebRequest -Uri $appUrl -UseBasicParsing -TimeoutSec 2; $auth = Invoke-WebRequest -Uri $authUrl -UseBasicParsing -TimeoutSec 2; if ($app.StatusCode -eq 200 -and $auth.StatusCode -eq 200) { $ok=$true; break } } catch {} }; if ($ok) { if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' $appUrl } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' $appUrl } else { Start-Process $appUrl }; exit 0 } else { Write-Host 'Enterprise client backend or API did not become ready in time.'; exit 1 }"
if errorlevel 1 (
  echo Enterprise client backend or API did not become ready. Please check the backend window for logs.
  exit /b 1
)

echo Started AGV enterprise client launcher.
endlocal
