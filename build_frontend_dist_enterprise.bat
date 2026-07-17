@echo off
setlocal

echo === Build Enterprise Frontend Dist ===
cd /d %~dp0frontend
set "VITE_CLIENT_VARIANT=enterprise"
call npm run build -- --outDir dist-enterprise
if errorlevel 1 (
  echo Enterprise frontend build failed.
  exit /b 1
)

echo Enterprise frontend dist build completed.
endlocal
