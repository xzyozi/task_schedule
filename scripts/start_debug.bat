@echo off
echo Starting development servers for debugging...

set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

IF EXIST "venv\Scripts\activate.bat" (
    CALL "venv\Scripts\activate.bat"
)

set "PYTHONPATH=%CD%\\src"

echo Starting Web GUI...
start "Web GUI" cmd /k "python src/webgui/app.py"

echo Starting FastAPI scheduler in this window...
python src/main.py

popd
