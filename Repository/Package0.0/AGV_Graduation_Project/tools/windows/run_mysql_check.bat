@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
cd /d %PROJECT_ROOT%\backend
call .\venv\Scripts\activate
set AGV_DATA_BACKEND=mysql

if "%AGV_DATABASE_AUTO_CREATE%"=="" (
  set AGV_DATABASE_AUTO_CREATE=true
)

python .\scripts\mysql_config_check.py
pause

endlocal
