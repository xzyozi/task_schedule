@echo off
echo Starting FastAPI backend (with auto-reload) and Flask Web GUI...

:: Get the directory of the current script (e.g., C:\path\to\project\scripts\)
set SCRIPT_DIR=%~dp0

:: Start FastAPI backend in a new console window with auto-reload
:: The 'cd /d' changes directory and '/d' allows changing drive if needed.
:: The '&&' ensures the uvicorn command only runs if cd is successful.
start "FastAPI Backend" cmd /k "cd /d "%SCRIPT_DIR%.." && uvicorn src.scheduler.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Flask Web GUI in a new console window (Flask's dev server has its own reloader)
start "Flask Web GUI" cmd /k "cd /d "%SCRIPT_DIR%.." && python src/webgui/app.py"

echo Development servers started.
echo FastAPI: http://127.0.0.1:8000
echo Flask Web GUI: http://127.0.0.1:5012
echo Close the console windows to stop the servers.