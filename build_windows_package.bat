@echo off
setlocal

echo === AGV Windows Package Build ===
set /p AGV_VERSION=<"%~dp0VERSION"
set "ROOT_PACKAGE_DIR=%~dp0dist\AGV_Dispatch_Package_%AGV_VERSION%"
set "PYI_PACKAGE_DIR=%~dp0backend\dist\AGV_Dispatch_Package"
set "DEMO_SOURCE_DIR=%~dp0demo"

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
if exist "%~dp0data\agv_dispatch.db" copy /Y "%~dp0data\agv_dispatch.db" "%ROOT_PACKAGE_DIR%\data\agv_dispatch.db" >nul
if not exist "%ROOT_PACKAGE_DIR%\demo" mkdir "%ROOT_PACKAGE_DIR%\demo"
if exist "%DEMO_SOURCE_DIR%\*" xcopy "%DEMO_SOURCE_DIR%\*" "%ROOT_PACKAGE_DIR%\demo\" /E /I /Y >nul
if not exist "%ROOT_PACKAGE_DIR%\demo\docs" mkdir "%ROOT_PACKAGE_DIR%\demo\docs"
if not exist "%ROOT_PACKAGE_DIR%\docs" mkdir "%ROOT_PACKAGE_DIR%\docs"
copy /Y "%~dp0start_agv.bat" "%ROOT_PACKAGE_DIR%\start_agv.bat" >nul
copy /Y "%~dp0VERSION" "%ROOT_PACKAGE_DIR%\VERSION" >nul
copy /Y "%~dp0docs\release\PACKAGING_WINDOWS.md" "%ROOT_PACKAGE_DIR%\docs\PACKAGING_WINDOWS.md" >nul
copy /Y "%~dp0docs\deployment\DATABASE_MIGRATIONS.md" "%ROOT_PACKAGE_DIR%\docs\DATABASE_MIGRATIONS.md" >nul
copy /Y "%~dp0docs\demo\DEMO_SCRIPT_MINIMUM_DELIVERY.md" "%ROOT_PACKAGE_DIR%\demo\docs\DEMO_SCRIPT_MINIMUM_DELIVERY.md" >nul
copy /Y "%~dp0docs\demo\QUICKSTART_MINIMUM_DELIVERY.md" "%ROOT_PACKAGE_DIR%\demo\docs\QUICKSTART_MINIMUM_DELIVERY.md" >nul
copy /Y "%~dp0docs\demo\SQLITE_DEMO_GUIDE.md" "%ROOT_PACKAGE_DIR%\demo\docs\SQLITE_DEMO_GUIDE.md" >nul
copy /Y "%~dp0docs\demo\TROUBLESHOOTING_MINIMUM_DELIVERY.md" "%ROOT_PACKAGE_DIR%\demo\docs\TROUBLESHOOTING_MINIMUM_DELIVERY.md" >nul

echo Package build completed:
echo   %ROOT_PACKAGE_DIR%
endlocal
