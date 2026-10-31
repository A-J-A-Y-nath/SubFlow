import re
from typing import Tuple, List

# Special character set for validation
SPECIAL_CHAR_PATTERN = r"""[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]"""


def validate_password(password: str | None) -> Tuple[bool, List[str]]:
    """
    Validate password requirements:
    - More than 8 characters in length (i.e., at least 9 characters)
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one special character
    """
    errors: List[str] = []

    if not password:
        return False, ["Password is required"]

    if len(password) <= 8:
        errors.append("Password must be more than 8 characters long (minimum 9 characters)")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(SPECIAL_CHAR_PATTERN, password):
        errors.append("Password must contain at least one special character (e.g. !@#$%^&*)")

    return len(errors) == 0, errors


def validate_email(email: str | None) -> bool:
    """Validate standard email syntax."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))
