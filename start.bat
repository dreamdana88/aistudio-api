@echo off
set CLOAKBROWSER_AUTO_UPDATE=false
set PYTHONPATH=%~dp0src
cd /d %~dp0
echo Installing dependencies...
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo Failed to install dependencies. Please make sure Python 3.11+ is installed.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.
echo Starting aistudio-api proxy...
echo Browser will be downloaded automatically on first run.
echo If download fails, please manually download from:
echo   https://github.com/CloakHQ/cloakbrowser/releases
echo.
python -m uvicorn aistudio_api.api.app:app --host 127.0.0.1 --port 8080
pause
