@echo off
REM This script starts only the Flask WebGUI.
REM It accepts optional arguments for Flask, e.g., --port 5001

REM Activate the virtual environment if it exists
IF EXIST "venv\Scripts\activate.bat" (
    CALL "venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found at venv\Scripts\activate.bat.
    echo Please ensure you have installed the project dependencies.
)

REM Set FLASK_APP environment variable
set FLASK_APP=webgui.app

REM Run the Flask WebGUI with arguments passed from the command line
REM Example: start_webgui_only.bat --port 5001 --debug
python -m flask run --host 0.0.0.0 %*

pause