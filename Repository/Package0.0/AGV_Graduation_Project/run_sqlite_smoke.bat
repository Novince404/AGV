@echo off
setlocal

cd /d %~dp0backend
call .\venv\Scripts\activate
set AGV_DATA_BACKEND=sqlite
set AGV_DATABASE_URL=sqlite:///./agv_dispatch_smoke.db
set AGV_DATABASE_AUTO_CREATE=true
python .\scripts\sqlite_smoke_check.py

endlocal
