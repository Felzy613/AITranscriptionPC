@echo off
cd /d "%~dp0"
echo ============================================
echo  AI Voice Transcription - Setup
echo ============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

if not exist .env (
    echo Creating .env template...
    echo OPENAI_API_KEY=sk-your-key-here> .env
    echo.
    echo *** IMPORTANT: Edit .env and replace sk-your-key-here with your real OpenAI API key ***
    echo *** Get your key at: https://platform.openai.com/api-keys ***
    echo.
)

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit .env and add your OpenAI API key
echo   2. Run the app:  venv\Scripts\pythonw.exe main.py
echo      (Use pythonw.exe to run without a console window)
echo.
echo To run WITH console for debugging:
echo      venv\Scripts\python.exe main.py
echo.
pause
