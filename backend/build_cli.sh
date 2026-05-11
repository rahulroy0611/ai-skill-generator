#!/bin/bash
set -e

echo "Building AI Skill Generator CLI..."

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -q pdfplumber sentence-transformers pyinstaller

echo "Building executable..."
pyinstaller --onefile --console --strip --name ai-skill-generator cli.py

echo ""
echo "Build complete!"
echo "Executable: dist/ai-skill-generator"