"""
Helper functions for TOTP generation
"""
import subprocess
import os
from pathlib import Path


def generate_otp(secret_key: str = None) -> str:
    """
    Generate TOTP code using the generateOTP.py script
    
    Args:
        secret_key: TOTP secret key. If None, reads from environment variable TOTP_SECRET_KEY
    
    Returns:
        TOTP code as string
    """
    if secret_key is None:
        secret_key = os.getenv("TOTP_SECRET_KEY")
        if not secret_key:
            raise ValueError("TOTP_SECRET_KEY not found in environment variables")
    
    # Get the script path (same directory as this file's parent)
    script_path = Path(__file__).parent.parent / "generateOTP.py"
    
    try:
        result = subprocess.run(
            ["python3", str(script_path), secret_key],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to generate OTP: {e.stderr}")
    except FileNotFoundError:
        raise FileNotFoundError("generateOTP.py script not found")

