import re

import bcrypt


class PasswordValidator:
    """Password strength validator"""

    MIN_LENGTH = 8
    MAX_LENGTH = 128
    MAX_BCRYPT_BYTES = 72

    @classmethod
    def validate(cls, password: str) -> tuple[bool, str]:
        """
        Validate password strength

        Returns:
            (is_valid, error_message)
        """
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters long"

        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must not exceed {cls.MAX_LENGTH} characters"

        if len(password.encode("utf-8")) > cls.MAX_BCRYPT_BYTES:
            return False, f"Password must not exceed {cls.MAX_BCRYPT_BYTES} UTF-8 bytes"

        # Check for uppercase letter
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        # Check for lowercase letter
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        # Check for digit
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        # Check for special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        # Check for common weak passwords
        weak_passwords = ["password", "12345678", "qwerty", "abc123", "password123"]
        if password.lower() in weak_passwords:
            return False, "This password is too common. Please choose a stronger password"

        return True, ""

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash password using bcrypt"""
        password_bytes = password.encode("utf-8")
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:
            return False
