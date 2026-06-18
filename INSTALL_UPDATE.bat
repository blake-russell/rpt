@echo off
setlocal EnableDelayedExpansion

echo.
echo =========================================================
echo   RPT - Retirement Planning Tool
echo   Install / Update Script
echo =========================================================
echo.

:: ── Check Windows platform ────────────────────────────────────────────────────
echo [1/6] Checking platform...
if not "%OS%"=="Windows_NT" (
    echo ERROR: This script only runs on Windows.
    pause
    exit /b 1
)

:: Detect Windows version (10 or 11)
for /f "tokens=4-5 delims=. " %%i in ('ver') do set WIN_VER=%%i.%%j
echo        Windows detected: !WIN_VER!

:: ── Check / Install Git ────────────────────────────────────────────────────────
echo.
echo [2/6] Checking for Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo Git is not installed. Would you like to install it now?
    echo   - Automated install via winget ^(Windows 10/11 recommended^)
    echo   - Or manually download from: https://git-scm.com/download/win
    echo.
    choice /C YN /M "Install Git automatically via winget?"
    if !errorlevel!==1 (
        echo Installing Git via winget...
        winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
        if !errorlevel! neq 0 (
            echo.
            echo winget install failed. Please install Git manually:
            echo   https://github.com/git-for-windows/git/releases/latest
            echo   ^(Download Git-*-64-bit.exe and run it^)
            echo.
            pause
            exit /b 1
        )
        :: Refresh PATH so git is available in this session
        call RefreshEnv.cmd >nul 2>&1
        set "PATH=%PATH%;C:\Program Files\Git\cmd"
    ) else (
        echo.
        echo Please install Git from: https://git-scm.com/download/win
        echo Then re-run this script.
        pause
        exit /b 1
    )
)
for /f "tokens=3" %%v in ('git --version') do set GIT_VER=%%v
echo        Git found: !GIT_VER!

:: ── Update repo (git pull) ─────────────────────────────────────────────────────
echo.
echo [3/6] Updating application files...

:: Check if we are inside a git repo
git rev-parse --is-inside-work-tree >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo This folder is not a git repository.
    echo If you downloaded RPT as a ZIP, you can re-download the latest version from GitHub.
    echo Skipping update step.
) else (
    echo        Pulling latest changes from remote...
    git pull
    if !errorlevel! neq 0 (
        echo        WARNING: git pull encountered an issue. Continuing with existing files.
    ) else (
        echo        Update complete.
    )
)

:: ── Check / Install Python 3.13 ───────────────────────────────────────────────
echo.
echo [4/6] Checking for Python 3.13+...

set PYTHON_OK=0
:: Try python3 first, then python
for %%P in (python3 python) do (
    if !PYTHON_OK!==0 (
        %%P --version >nul 2>&1
        if !errorlevel!==0 (
            for /f "tokens=2" %%v in ('%%P --version 2^>^&1') do set PY_VER=%%v
            for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
                if %%a GEQ 3 if %%b GEQ 13 (
                    set PYTHON_CMD=%%P
                    set PYTHON_OK=1
                )
            )
        )
    )
)

if !PYTHON_OK!==0 (
    echo.
    echo Python 3.13 or later is not installed. Would you like to install it now?
    echo   - Automated install via winget ^(Windows 10/11 recommended^)
    echo   - Or manually download from: https://www.python.org/downloads/
    echo.
    choice /C YN /M "Install Python 3.13 automatically via winget?"
    if !errorlevel!==1 (
        echo Installing Python 3.13 via winget...
        winget install --id Python.Python.3.13 -e --source winget --accept-package-agreements --accept-source-agreements
        if !errorlevel! neq 0 (
            echo.
            echo winget install failed. Please install Python manually:
            echo   https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
            echo   IMPORTANT: Check "Add Python to PATH" during installation!
            echo.
            pause
            exit /b 1
        )
        :: Refresh PATH
        set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts"
        set PYTHON_CMD=python
    ) else (
        echo.
        echo Please install Python 3.13 from:
        echo   https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
        echo IMPORTANT: Check "Add Python to PATH" during installation!
        pause
        exit /b 1
    )
)
echo        Python found: !PYTHON_CMD! !PY_VER!

:: ── Set up virtual environment ─────────────────────────────────────────────────
echo.
echo [5/6] Setting up virtual environment...

if not exist ".venv" (
    echo        Creating virtual environment...
    !PYTHON_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        Virtual environment created.
) else (
    echo        Virtual environment already exists.
)

:: Activate and install dependencies
echo        Installing / updating Python dependencies...
call .venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if !errorlevel! neq 0 (
    echo ERROR: pip install failed. Check requirements.txt and your internet connection.
    pause
    exit /b 1
)
echo        Dependencies installed.

:: ── Run Django migrations and check ───────────────────────────────────────────
echo.
echo [6/6] Running database setup and configuration check...

python manage.py migrate --run-syncdb
if !errorlevel! neq 0 (
    echo ERROR: Database migration failed.
    pause
    exit /b 1
)

python manage.py check
if !errorlevel! neq 0 (
    echo ERROR: Django configuration check failed.
    pause
    exit /b 1
)

:: ── Create default superuser if no users exist ────────────────────────────────
echo.
echo Checking for existing users...
for /f %%c in ('python -c "import django; import os; os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\",\"rpt.settings\"); django.setup(); from django.contrib.auth.models import User; print(User.objects.count())"') do set USER_COUNT=%%c

if "!USER_COUNT!"=="0" (
    echo.
    echo Creating default admin account...
    python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','rpt.settings'); django.setup(); from django.contrib.auth.models import User; User.objects.create_superuser('admin','','Rpt@2025!k3')"
    echo.
    echo        Default account created:
    echo          Username : admin
    echo          Password : Rpt@2025!k3
    echo.
    echo        IMPORTANT: Change your password after first login at:
    echo          http://127.0.0.1:8000/admin/password_change/
    echo.
) else (
    echo        Existing user account found ^(!USER_COUNT! user^(s^)^).
)

echo.
echo =========================================================
echo   Setup complete!
echo.
echo   To start the app, run:  START.bat
echo   Then open:              http://127.0.0.1:8000
echo =========================================================
echo.
pause
