@echo off
setlocal

echo === Build Frontend Dist ===
cd /d %~dp0frontend\agv-frontend
call npm run build
if errorlevel 1 (
  echo Frontend build failed.
  exit /b 1
)

echo Frontend dist build completed.
endlocal
