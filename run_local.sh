#!/bin/bash
# Run Flask locally

echo "🚀 Starting Flask locally..."
echo "📝 Make sure you have:"
echo "   1. Virtual environment activated"
echo ""
echo "🌐 Flask will be available at: http://localhost:5000"
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Flask
cd "$(dirname "$0")"
python3 api/app.py

