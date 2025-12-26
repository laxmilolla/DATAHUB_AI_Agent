#!/bin/bash
set -e

echo "===================================="
echo "AI Agent QA - Setup Script"
echo "===================================="
echo

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    exit 1
fi
echo "✅ Node.js $(node --version)"
echo

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"
echo

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python dependencies installed"
echo

# Install Node dependencies
echo "Installing Node.js dependencies..."
cd mcp-server
npm install
npx playwright install chromium
echo "✅ Node.js dependencies installed"
echo

cd "$PROJECT_ROOT"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env and add your AWS credentials"
fi

# Create necessary directories
mkdir -p storage/executions
mkdir -p storage/screenshots
echo "✅ Storage directories created"
echo

echo "===================================="
echo "✅ Setup complete!"
echo "===================================="
echo
echo "Next steps:"
echo "1. Edit .env and add your AWS credentials"
echo "2. Run: ./scripts/start.sh"
echo


