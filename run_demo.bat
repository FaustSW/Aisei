@echo off
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found at venv\Scripts\activate.bat
    echo Continuing with system Python...
)

python run_demo.py
pause