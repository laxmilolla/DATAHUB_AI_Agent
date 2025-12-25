#!/bin/bash
set -e

echo "===================================="
echo "AI Agent QA - Starting Services"
echo "===================================="
echo

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found. Run ./scripts/setup.sh first"
    exit 1
fi

# Check AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "❌ AWS_ACCESS_KEY_ID not set in .env"
    exit 1
fi
echo "✅ AWS credentials configured"
echo

echo "Starting Flask API on http://localhost:5000"
echo "===================================="
echo

# Start Flask
cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
python -m api.app

