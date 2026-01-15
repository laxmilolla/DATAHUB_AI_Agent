#!/bin/bash
# Run Flask locally for Instructions → Test Cases Generator
# This allows you to see the browser and manually set up preconditions

echo "🚀 Starting Flask locally for Instructions Generator..."
echo ""
echo "📝 This will allow you to:"
echo "   1. See the browser (for manual login/TOTP)"
echo "   2. Set up preconditions manually"
echo "   3. Run test instructions"
echo "   4. Get XPaths and Excel test cases"
echo ""
echo "🌐 Access at: http://localhost:5000/instructions"
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Flask
cd "$(dirname "$0")"
python3 api/app.py

