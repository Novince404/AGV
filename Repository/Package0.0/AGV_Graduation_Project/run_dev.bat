@echo off
setlocal

rem Start backend with venv
start "AGV Backend" cmd /k "cd /d %~dp0backend && call .\venv\Scripts\activate && python -m uvicorn main:app --reload"

rem Start frontend
start "AGV Frontend" cmd /k "cd /d %~dp0frontend\agv-frontend && npm run dev"

rem Browser auto-open disabled by request

echo Started backend and frontend in separate windows.
endlocal
