@echo off
REM This script starts the Task Scheduler and the WebGUI in separate windows.

REM Start the Flask WebGUI server in a new window
echo Launching WebGUI server in a new window...
START "Flask WebGUI" cmd /c start_flask_server.bat

REM Activate the virtual environment for the main scheduler
IF EXIST "%~dp0venv\Scripts\activate.bat" (
    echo Activating virtual environment for scheduler...
    CALL "%~dp0p0venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found.
)

REM Give the GUI server a moment to start up
timeout /t 3 /nobreak >nul

echo Starting the main task scheduler...
REM Run the main task scheduler application
task-scheduler

pause
