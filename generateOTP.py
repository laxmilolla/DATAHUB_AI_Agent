#!/usr/bin/env python3
import sys
import pyotp

def main():
    if len(sys.argv) < 2:
        print("Error: Missing secret key argument.", file=sys.stderr)
        sys.exit(1)

    secret = sys.argv[1].strip()

    try:
        totp = pyotp.TOTP(secret)
        print(totp.now())  # Output ONLY the OTP
    except Exception as e:
        print(f"Error generating OTP: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

