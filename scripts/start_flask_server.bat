@echo off
REM This script starts the Flask WebGUI server.

echo Starting Flask WebGUI Server...

REM Activate the virtual environment if it exists
IF EXIST "%~dp0venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    CALL "%~dp0venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found.
)

REM Set the FLASK_APP environment variable
set FLASK_APP=webgui.app

echo Launching Flask server on port 5012...
REM Run the flask server
python -m flask run --host=0.0.0.0 --port=5012

pause
