#!/bin/bash
# Run Flask locally for Experiment Area with CDP support

echo "🚀 Starting Flask locally..."
echo "📝 Make sure you have:"
echo "   1. Virtual environment activated"
echo "   2. Chrome started with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug"
echo ""
echo "🌐 Flask will be available at: http://localhost:5000"
echo "🧪 Experiment Area: http://localhost:5000/experiment"
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Flask
cd "$(dirname "$0")"
python3 api/app.py

