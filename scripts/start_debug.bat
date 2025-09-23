@echo off
echo Starting development servers for debugging...

set "PROJECT_ROOT=%~dp0.."
pushd "%PROJECT_ROOT%"

IF EXIST "venv\Scripts\activate.bat" (
    CALL "venv\Scripts\activate.bat"
)

set "FLASK_APP=src.webgui.app"
start "Web GUI" cmd /k "python -m flask run --host=0.0.0.0 --port=5012"

echo Starting FastAPI scheduler in this window...
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

popd