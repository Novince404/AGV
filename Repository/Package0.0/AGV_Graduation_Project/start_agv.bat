@echo off
setlocal

set "AGV_HOST=127.0.0.1"
set "AGV_PORT=8000"
set "APP_URL=http://%AGV_HOST%:%AGV_PORT%/"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

if exist "%~dp0backend.exe" (
  start "AGV Backend Package" cmd /c "set AGV_HOST=%AGV_HOST% && set AGV_PORT=%AGV_PORT% && \"%~dp0backend.exe\""
) else (
  call "%~dp0run_packaged_dev.bat"
  exit /b %errorlevel%
)

start "AGV Browser" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; if (Test-Path '%CHROME_EXE%') { Start-Process '%CHROME_EXE%' '%APP_URL%' } elseif (Get-Command chrome -ErrorAction SilentlyContinue) { Start-Process 'chrome' '%APP_URL%' } else { Start-Process '%APP_URL%' }"

echo Started AGV package launcher.
endlocal
