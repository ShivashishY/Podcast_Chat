@echo off
:: Podcast Chat - Windows One-Click Launcher
:: Double-click this file to start Podcast Chat!

title Podcast Chat - Starting...
cd /d "%~dp0"

echo.
echo  🎙️  Podcast Chat - Windows Setup
echo  =================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please install Python 3.10 or higher from:
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [OK] Python is installed

:: Check if FFmpeg is installed
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg is not installed.
    echo.
    echo Please install FFmpeg:
    echo 1. Download from: https://ffmpeg.org/download.html
    echo 2. Or use: winget install ffmpeg
    echo 3. Or use: choco install ffmpeg
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

echo [OK] FFmpeg check complete

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo.
    echo Creating Python virtual environment...
    python -m venv .venv
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Install/update dependencies
echo.
echo Installing Python packages...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo [OK] Dependencies installed

:: Create .env file if it doesn't exist
if not exist ".env" (
    echo.
    echo Creating .env file...
    copy .env.example .env >nul
    echo [NOTE] Please edit .env and add your SMALLEST_API_KEY
)

:: Check if Ollama is installed
ollama --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Ollama is not installed.
    echo.
    echo For AI chat features, please install Ollama:
    echo https://ollama.ai/download
    echo.
    echo Press any key to continue without AI chat...
    pause >nul
) else (
    echo [OK] Ollama is installed
    
    :: Start Ollama if not running
    tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
    if errorlevel 1 (
        echo Starting Ollama...
        start /B ollama serve >nul 2>&1
        timeout /t 3 >nul
    )
    
    :: Check if model exists
    ollama list 2>nul | findstr /C:"llama3.2" >nul
    if errorlevel 1 (
        echo.
        echo Downloading AI model (first time only, please wait)...
        ollama pull llama3.2
    )
    echo [OK] AI model ready
)

:: Start the application
echo.
echo ==========================================
echo.
echo   Starting Podcast Chat...
echo.
echo   Open your browser to:
echo   http://localhost:5000
echo.
echo ==========================================
echo.
echo Press Ctrl+C to stop the app
echo.

python app.py

pause
