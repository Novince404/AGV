@echo off
setlocal

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
cd /d %PROJECT_ROOT%\backend
call .\venv\Scripts\activate
set AGV_DATA_BACKEND=sqlite
set AGV_DATABASE_URL=sqlite:///./agv_dispatch_smoke.db
set AGV_DATABASE_AUTO_CREATE=true
python .\scripts\sqlite_smoke_check.py

endlocal
