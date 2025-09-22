@echo off
echo Starting FastAPI backend (with auto-reload) and Flask Web GUI...

:: Start FastAPI backend in a new console window with auto-reload
:: --host 0.0.0.0 allows access from other machines on the network
start "FastAPI Backend" cmd /k "uvicorn src.scheduler.main:app --reload --host 0.0.0.0 --port 8000"

:: Start Flask Web GUI in a new console window (Flask's dev server has its own reloader)
:: Set FLASK_PORT if you want to change the default 5012
start "Flask Web GUI" cmd /k "python src/webgui/app.py"

echo Development servers started.
echo FastAPI: http://127.0.0.1:8000
echo Flask Web GUI: http://127.0.0.1:5012
echo Close the console windows to stop the servers.