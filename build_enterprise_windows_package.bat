@echo off
setlocal

echo === AGV Enterprise Client Package Build ===
set /p AGV_VERSION=<"%~dp0VERSION"
set "ROOT_PACKAGE_DIR=%~dp0dist\AGV_Enterprise_Client_%AGV_VERSION%"
set "PYI_PACKAGE_DIR=%~dp0backend\dist\AGV_Enterprise_Client"
set "PYI_BUILD_DIR=%~dp0backend\build\backend_enterprise"
set "ENTERPRISE_DOCS_DIR=%~dp0enterprise_client\docs"
set "DEMO_SOURCE_DIR=%~dp0demo"

call "%~dp0build_frontend_dist_enterprise.bat"
if errorlevel 1 exit /b 1

cd /d %~dp0
set "PACKAGE_PYTHON=%~dp0backend\venv\Scripts\python.exe"

"%PACKAGE_PYTHON%" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if errorlevel 1 (
  echo PyInstaller is not installed in backend venv.
  echo Install it with:
  echo   backend\venv\Scripts\python.exe -m pip install -r backend\requirements-package.txt
  exit /b 1
)

if exist "%PYI_BUILD_DIR%" rmdir /s /q "%PYI_BUILD_DIR%"
if exist "%PYI_PACKAGE_DIR%" rmdir /s /q "%PYI_PACKAGE_DIR%"

"%PACKAGE_PYTHON%" -m PyInstaller --noconfirm --distpath backend\dist --workpath backend\build backend\packaging\backend_enterprise.spec
if errorlevel 1 (
  echo Enterprise PyInstaller build failed.
  exit /b 1
)
if not exist "%PYI_PACKAGE_DIR%\backend.exe" (
  echo Enterprise PyInstaller build did not produce backend.exe.
  exit /b 1
)

if exist "%ROOT_PACKAGE_DIR%" rmdir /s /q "%ROOT_PACKAGE_DIR%"
if not exist "%ROOT_PACKAGE_DIR%" mkdir "%ROOT_PACKAGE_DIR%"
xcopy "%PYI_PACKAGE_DIR%\*" "%ROOT_PACKAGE_DIR%\" /E /I /Y >nul
if not exist "%ROOT_PACKAGE_DIR%\data" mkdir "%ROOT_PACKAGE_DIR%\data"
if exist "%~dp0data\agv_dispatch.db" (
  copy /Y "%~dp0data\agv_dispatch.db" "%ROOT_PACKAGE_DIR%\data\agv_dispatch.db" >nul
) else if exist "%~dp0data\agv_enterprise_client.db" (
  copy /Y "%~dp0data\agv_enterprise_client.db" "%ROOT_PACKAGE_DIR%\data\agv_dispatch.db" >nul
)
if exist "%~dp0backend\.env" (
  copy /Y "%~dp0backend\.env" "%ROOT_PACKAGE_DIR%\.env" >nul
)
if not exist "%ROOT_PACKAGE_DIR%\docs" mkdir "%ROOT_PACKAGE_DIR%\docs"
if exist "%ENTERPRISE_DOCS_DIR%\*" xcopy "%ENTERPRISE_DOCS_DIR%\*" "%ROOT_PACKAGE_DIR%\docs\" /E /I /Y >nul
copy /Y "%~dp0docs\release\PACKAGING_WINDOWS.md" "%ROOT_PACKAGE_DIR%\docs\PACKAGING_WINDOWS.md" >nul
copy /Y "%~dp0docs\deployment\DATABASE_MIGRATIONS.md" "%ROOT_PACKAGE_DIR%\docs\DATABASE_MIGRATIONS.md" >nul
if not exist "%ROOT_PACKAGE_DIR%\demo" mkdir "%ROOT_PACKAGE_DIR%\demo"
if exist "%DEMO_SOURCE_DIR%\docs\*" xcopy "%DEMO_SOURCE_DIR%\docs\*" "%ROOT_PACKAGE_DIR%\demo\docs\" /E /I /Y >nul
if exist "%DEMO_SOURCE_DIR%\json\*" xcopy "%DEMO_SOURCE_DIR%\json\*" "%ROOT_PACKAGE_DIR%\demo\json\" /E /I /Y >nul
copy /Y "%~dp0start_enterprise_client.bat" "%ROOT_PACKAGE_DIR%\start_enterprise_client.bat" >nul
copy /Y "%~dp0VERSION" "%ROOT_PACKAGE_DIR%\VERSION" >nul

echo Enterprise client package build completed:
echo   %ROOT_PACKAGE_DIR%
endlocal
