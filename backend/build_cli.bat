@echo off
setlocal

echo Building AI Skill Generator CLI...
cd /d "%~dp0"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing dependencies...
pip install -q pdfplumber sentence-transformers pyinstaller

echo Building executable...
pyinstaller --onefile --console --strip --name ai-skill-generator cli.py

echo.
echo Build complete!
echo Executable: dist\ai-skill-generator.exe
echo.
pause