@echo off
setlocal
echo =======================================================
echo          WinQRReader - Windows 11 WiFi QR Scanner
echo =======================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.10+ from python.org.
    pause
    exit /b 1
)

:: Install / verify dependencies
echo Checking dependencies...
python -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Dependency check encountered an issue. Attempting to start app anyway...
)

:: Run Application
echo Starting WinQRReader...
python main.py

endlocal
