@echo off
REM This script starts the Flask WebGUI server.

echo Starting Flask WebGUI Server...

:: Get the directory of the current script (e.g., C:\path\to\project\scripts\)
set SCRIPT_DIR=%~dp0

:: Change to the project root directory
pushd "%SCRIPT_DIR%.."

REM Activate the virtual environment if it exists
IF EXIST "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    CALL "venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found.
)

REM Set the FLASK_APP environment variable
set FLASK_APP=src.webgui.app

echo Launching Flask server on port 5012...
REM Run the flask server
python -m flask run --host=0.0.0.0 --port=5012

:: Change back to the original directory
popd

pause

