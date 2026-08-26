@echo off
set PYTHONDONTWRITEBYTECODE=1
echo Starting development servers for debugging...

set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

IF EXIST "venv\Scripts\activate.bat" (
    CALL "venv\Scripts\activate.bat"
)

set "PYTHONPATH=%CD%\src"

echo Starting Task Scheduler Application (FastAPI)...
python -B src/main.py

popd

