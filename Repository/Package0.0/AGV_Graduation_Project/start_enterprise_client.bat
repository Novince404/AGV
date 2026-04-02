@echo off
setlocal

set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8010"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

if exist "%~dp0backend.exe" (
  start "AGV Enterprise Client Backend" "%~dp0backend.exe"
) else (
  call "%~dp0run_enterprise_packaged_dev.bat"
  exit /b %errorlevel%
)

echo Waiting for enterprise client backend on %APP_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for ($i=0; $i -lt 20; $i++) { Start-Sleep -Milliseconds 500; try { $res = Invoke-WebRequest -Uri '%APP_URL%' -UseBasicParsing -TimeoutSec 2; if ($res.StatusCode -eq 200) { $ok=$true; break } } catch {} }; if ($ok) { if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }; exit 0 } else { Write-Host 'Enterprise client backend did not become ready in time.'; exit 1 }"
if errorlevel 1 (
  echo Enterprise client backend did not become ready. Please check the backend window for logs.
  exit /b 1
)

echo Started AGV enterprise client launcher.
endlocal
