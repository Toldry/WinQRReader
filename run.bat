@echo off
setlocal
echo =======================================================
echo          WinQRReader - Windows 11 WiFi QR Scanner
echo =======================================================
echo.

:: Check uv installation
uv --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] uv is not found in PATH. Install it with:
    echo         powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

:: Run Application (uv creates .venv and installs locked dependencies on first run)
echo Starting WinQRReader...
uv run --locked --no-dev main.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WinQRReader exited with an error. See the console output above.
    pause
)

endlocal
