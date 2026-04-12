#!/bin/bash
set -e

echo "🎙️  Voice Dictate — Setup"
echo "========================="
echo ""

# Check Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "❌ Voice Dictate requires Apple Silicon (M1/M2/M3/M4)."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VERSION detected"

# Create venv
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing dependencies..."
.venv/bin/pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Run:  ./start.sh"
echo ""
echo "⚠️  First run downloads the model (~5.5 GB) — this takes a few minutes."
echo "⚠️  macOS will ask for Microphone, Accessibility, and Input Monitoring permissions."
