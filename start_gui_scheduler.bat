@echo off
REM This script starts the Task Scheduler with the WebGUI.

REM Activate the virtual environment if it exists
IF EXIST "venv\Scripts\activate.bat" (
    CALL "venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found at venv\Scripts\activate.bat.
    echo Please ensure you have installed the project dependencies.
)

REM Run the task-scheduler with the --with-gui argument
task-scheduler --with-gui

pause