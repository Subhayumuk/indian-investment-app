@echo off
REM Start the FastAPI dev server without activating the virtual environment.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating .venv and installing dependencies...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

".venv\Scripts\python.exe" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
