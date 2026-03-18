@echo off
setlocal

echo === AGV Windows Package Build ===
set "ROOT_PACKAGE_DIR=%~dp0dist\AGV_Dispatch_Package"
set "PYI_PACKAGE_DIR=%~dp0backend\dist\AGV_Dispatch_Package"

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

if not exist "%ROOT_PACKAGE_DIR%" mkdir "%ROOT_PACKAGE_DIR%"
xcopy "%PYI_PACKAGE_DIR%\*" "%ROOT_PACKAGE_DIR%\" /E /I /Y >nul
if not exist "%ROOT_PACKAGE_DIR%\data" mkdir "%ROOT_PACKAGE_DIR%\data"
copy /Y "%~dp0start_agv.bat" "%ROOT_PACKAGE_DIR%\start_agv.bat" >nul

echo Package build completed:
echo   %ROOT_PACKAGE_DIR%
endlocal
