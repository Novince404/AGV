@echo off
setlocal

cd /d %~dp0backend
call .\venv\Scripts\activate
set AGV_DATA_BACKEND=mysql

if "%AGV_DATABASE_AUTO_CREATE%"=="" (
  set AGV_DATABASE_AUTO_CREATE=true
)

python .\scripts\mysql_config_check.py
pause

endlocal
