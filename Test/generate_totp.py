#!/usr/bin/env python3
"""
Generate TOTP code using pyotp (same library as Python tests)
Called from TypeScript tests to ensure same TOTP generation logic
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import pyotp

# Load environment variables from .env file
# Check multiple locations: same dir, parent, project root, home
env_locations = [
    Path(__file__).parent / '.env',  # Same directory as script
    Path(__file__).parent.parent / '.env',  # Parent directory
    Path(__file__).parent.parent.parent / '.env',  # Project root
    Path.home() / '.env',  # Home directory
]

env_loaded = False
for env_path in env_locations:
    if env_path.exists():
        load_dotenv(env_path)
        env_loaded = True
        break

if not env_loaded:
    print("⚠️  .env file not found", file=sys.stderr)

# Get secret key from command line argument or environment variable
if len(sys.argv) > 1:
    secret_key = sys.argv[1]
else:
    # Try user-specific key first, then generic keys
    user_email = os.getenv('TOTP_USER_EMAIL', '')
    if user_email:
        # Sanitize email for environment variable name
        email_sanitized = user_email.replace('@', '_').replace('.', '_').upper()
        secret_key = os.getenv(f'TOTP_SECRET_KEY_TS_{email_sanitized}') or \
                     os.getenv('TOTP_SECRET_KEY_TS') or \
                     os.getenv('TOTP_SECRET_KEY')
    else:
        secret_key = os.getenv('TOTP_SECRET_KEY_TS') or os.getenv('TOTP_SECRET_KEY')

if not secret_key:
    print("ERROR: TOTP secret key not found", file=sys.stderr)
    sys.exit(1)

# Generate TOTP code using pyotp (same as Python tests)
try:
    totp = pyotp.TOTP(secret_key)
    totp_code = totp.now()
    print(totp_code)  # Output just the code (for easy parsing)
    sys.exit(0)
except Exception as e:
    print(f"ERROR: Failed to generate TOTP: {e}", file=sys.stderr)
    sys.exit(1)


