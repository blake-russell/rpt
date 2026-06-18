@echo off
setlocal EnableDelayedExpansion

echo.
echo =========================================================
echo   RPT - Retirement Planning Tool
echo   Starting...
echo =========================================================
echo.

:: ── Check virtual environment ─────────────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please run INSTALL_UPDATE.bat first.
    echo.
    pause
    exit /b 1
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: ── Quick Django system check ─────────────────────────────────────────────────
echo Checking configuration...
python manage.py check
if !errorlevel! neq 0 (
    echo.
    echo Configuration check failed. Try running INSTALL_UPDATE.bat to repair.
    pause
    exit /b 1
)
echo Configuration OK.
echo.

:: ── Open browser after 2-second pause ────────────────────────────────────────
echo Starting server at http://127.0.0.1:8000
echo.
echo   Login at : http://127.0.0.1:8000
echo   Username : admin
echo   Password : Rpt@2025!k3  ^(default set by INSTALL_UPDATE.bat^)
echo              If you changed your password, use your new one.
echo.
echo Press Ctrl+C in this window to stop the server.
echo.

:: Use PowerShell to open the browser after a short delay in the background
start "" powershell -Command "Start-Sleep 2; Start-Process 'http://127.0.0.1:8000'"

:: Start Django dev server (blocking)
python manage.py runserver 127.0.0.1:8000
