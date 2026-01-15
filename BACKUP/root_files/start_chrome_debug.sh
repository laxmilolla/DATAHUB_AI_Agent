#!/bin/bash
# Script to start Chrome with remote debugging enabled

# Method 1: If Chrome is in Applications folder (macOS)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 &

# Alternative: If you have Chrome installed elsewhere, you can use:
# /Applications/Google Chrome.app/Contents/MacOS/Google Chrome --remote-debugging-port=9222 &

echo "Chrome started with remote debugging on port 9222"
echo "You can now navigate to your page and run the test script"

