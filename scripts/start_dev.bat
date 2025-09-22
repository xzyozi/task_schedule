@echo off
echo Starting development servers (FastAPI Scheduler and Flask WebGUI)...

:: Get the absolute path to the project root directory (one level up from this script)
set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

echo Project root directory: %CD%

:: Activate virtual environment
IF EXIST "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    CALL "venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found. Please run setup first.
    pause
    exit /b 1
)

:: Set PYTHONPATH to include the src directory
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
echo PYTHONPATH set to: %PYTHONPATH%

:: Start FastAPI scheduler in a new console window with auto-reload
echo Starting FastAPI scheduler (http://localhost:8000)
start "Scheduler (FastAPI)" cmd /k "uvicorn scheduler.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Flask Web GUI in a new console window with auto-reload
echo Starting Web GUI (http://localhost:5012)
set "FLASK_APP=webgui.app"
set "FLASK_ENV=development"
start "Web GUI (Flask)" cmd /k "python -m flask run --host=0.0.0.0 --port=5012"

echo.
echo Development servers are starting in separate windows.
echo You can close them individually to stop them.

popd
