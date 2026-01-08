"""
TOTP Handler - Handle TOTP code generation
Extracted from bedrock_playwright_agent.py lines 2720-2772, 2080-2120
"""
import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import will be done at runtime to avoid circular dependencies
# from utils.otp_helper import generate_otp


class TOTPHandler:
    """Handle TOTP code generation"""
    
    def __init__(self):
        """Initialize TOTP handler"""
        pass
    
    def is_totp_step(self, step_text: str, text: str = None) -> bool:
        """
        Detect if step is TOTP-related
        """
        totp_keywords = ["totp", "one-time", "one time", "2fa", "two-factor", "authenticator code", "security code"]
        step_has_totp = any(keyword in step_text.lower() for keyword in totp_keywords)
        text_has_totp = any(keyword in str(text).lower() for keyword in totp_keywords) if text else False
        return step_has_totp or text_has_totp
    
    def generate_code(self, story: str = None, text: str = None, secret_key: str = None) -> str:
        """
        Generate TOTP code
        Args:
            story: Story text to extract secret key from
            text: Text parameter to extract secret key from
            secret_key: Direct secret key (if provided, used first)
        Returns: 6-digit TOTP code
        """
        from utils.otp_helper import generate_otp
        
        # Use provided secret key first
        if not secret_key:
            secret_key = self._extract_secret_from_story(story)
        
        if not secret_key and text:
            secret_key = self._extract_secret_from_text(text)
        
        if not secret_key:
            secret_key = self._get_secret_from_env()
        
        # Generate TOTP code
        try:
            if secret_key:
                logger.info(f"  [TOTP] Generating TOTP code using secret key: {secret_key[:10]}...")
                totp_code = generate_otp(secret_key)
            else:
                # Use environment variable (generate_otp will handle it)
                logger.info(f"  [TOTP] Generating TOTP code using TOTP_SECRET_KEY from environment")
                totp_code = generate_otp()
            
            logger.info(f"  [TOTP] Generated TOTP code: {totp_code} (length: {len(totp_code)})")
            return totp_code
        except Exception as e:
            logger.error(f"  [TOTP] Failed to generate TOTP code: {e}")
            raise
    
    def _extract_secret_from_story(self, story: str) -> Optional[str]:
        """
        Extract secret key from story text
        """
        if not story:
            return None
        
        # Pattern 1: "secret key LCBUDA6NSWXUO4AKLTU6F3UXXO7QMBCX"
        secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
        match = re.search(secret_pattern, story, re.IGNORECASE)
        if match:
            secret_key = match.group(1)
            logger.info(f"  [TOTP] Extracted secret key from story: {secret_key[:10]}...")
            return secret_key
        
        # Pattern 2: Look for long alphanumeric strings in story
        long_alnum_pattern = r'\b([A-Z0-9]{20,})\b'
        matches = re.findall(long_alnum_pattern, story)
        if matches:
            secret_key = max(matches, key=len)
            logger.info(f"  [TOTP] Extracted potential secret key: {secret_key[:10]}...")
            return secret_key
        
        return None
    
    def _extract_secret_from_text(self, text: str) -> Optional[str]:
        """
        Extract secret key from text parameter
        """
        if not text:
            return None
        
        secret_pattern = r'(?:secret\s+key|key)\s+([A-Z0-9]{20,})'
        match = re.search(secret_pattern, str(text), re.IGNORECASE)
        if match:
            secret_key = match.group(1)
            logger.info(f"  [TOTP] Extracted secret key from text parameter: {secret_key[:10]}...")
            return secret_key
        
        return None
    
    def _get_secret_from_env(self) -> Optional[str]:
        """
        Get secret key from environment variable
        """
        secret_key = os.getenv("TOTP_SECRET_KEY")
        if secret_key:
            logger.info(f"  [TOTP] Using TOTP_SECRET_KEY from environment")
        return secret_key


