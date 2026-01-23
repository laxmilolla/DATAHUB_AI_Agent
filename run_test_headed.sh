#!/bin/bash
# Run Playwright test locally with headless=false (browser visible)

# Check if test file is provided
if [ -z "$1" ]; then
    echo "Usage: ./run_test_headed.sh <test-file.spec.ts> [test-directory]"
    echo ""
    echo "Examples:"
    echo "  ./run_test_headed.sh test_excel_xxx.spec.ts"
    echo "  ./run_test_headed.sh test_excel_xxx.spec.ts storage/excel_tests"
    exit 1
fi

TEST_FILE="$1"
TEST_DIR="${2:-storage/excel_tests}"

# Check if test file exists
if [ ! -f "$TEST_DIR/$TEST_FILE" ] && [ ! -f "$TEST_FILE" ]; then
    echo "❌ Test file not found: $TEST_FILE"
    echo "   Checked: $TEST_DIR/$TEST_FILE and $TEST_FILE"
    exit 1
fi

# Determine full path
if [ -f "$TEST_FILE" ]; then
    FULL_PATH=$(realpath "$TEST_FILE")
    TEST_DIR=$(dirname "$FULL_PATH")
    TEST_FILE=$(basename "$FULL_PATH")
else
    FULL_PATH=$(realpath "$TEST_DIR/$TEST_FILE")
    TEST_DIR=$(dirname "$FULL_PATH")
    TEST_FILE=$(basename "$FULL_PATH")
fi

echo "🚀 Running Playwright test with browser visible (headless=false)"
echo "   Test file: $TEST_FILE"
echo "   Directory: $TEST_DIR"
echo ""

# Change to test directory
cd "$TEST_DIR"

# Check if package.json exists, create if not
if [ ! -f "package.json" ]; then
    echo "📦 Creating package.json..."
    cat > package.json << 'EOF'
{
  "name": "playwright-test",
  "version": "1.0.0",
  "scripts": {
    "test": "playwright test"
  },
  "dependencies": {
    "@playwright/test": "^1.40.0",
    "dotenv": "^16.0.0",
    "otplib": "^12.0.0"
  }
}
EOF
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Install Playwright browsers if needed
echo "🌐 Ensuring Playwright browsers are installed..."
npx playwright install chromium

# Run test with --headed flag (headless=false)
echo ""
echo "▶️  Starting test (browser will be visible)..."
echo ""

# Remove CI=true from environment to allow headed mode
# Use --headed flag to show browser
npx playwright test "$TEST_FILE" --headed --reporter=list

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed successfully!"
else
    echo "❌ Test failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
