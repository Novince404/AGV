@echo off
setlocal

echo === AGV Windows Package Build ===

call "%~dp0build_frontend_dist.bat"
if errorlevel 1 exit /b 1

cd /d %~dp0backend
call .\venv\Scripts\activate

python -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if errorlevel 1 (
  echo PyInstaller is not installed in backend venv.
  echo Install it with:
  echo   backend\venv\Scripts\python.exe -m pip install -r backend\requirements-package.txt
  exit /b 1
)

python -m PyInstaller .\packaging\backend.spec --noconfirm --clean
if errorlevel 1 (
  echo PyInstaller build failed.
  exit /b 1
)

if not exist "%~dp0dist\AGV_Dispatch_Package\data" mkdir "%~dp0dist\AGV_Dispatch_Package\data"
copy /Y "%~dp0start_agv.bat" "%~dp0dist\AGV_Dispatch_Package\start_agv.bat" >nul

echo Package build completed:
echo   %~dp0dist\AGV_Dispatch_Package
endlocal
