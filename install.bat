@echo off
cd /d "%~dp0"
echo ============================================
echo  AI Transcription PC - Setup
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

if not exist .env if exist .env.example (
    echo Creating .env from template...
    copy /y .env.example .env >nul
    echo.
    echo Optional: edit .env to set OPENAI_API_KEY ahead of first launch.
    echo If you skip this, the app will prompt for the key when it starts.
    echo.
)

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo Run the app with:
echo   venv\Scripts\pythonw.exe main.py
echo.
echo For console output while debugging:
echo   venv\Scripts\python.exe main.py
echo.
pause
