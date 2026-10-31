import pytest
from backend.utils.validators import validate_password, validate_email


def test_password_validation_length():
    """Password must be more than 8 characters (> 8, so at least 9 chars)."""
    # 8 characters exactly with upper, lower, special
    valid, errors = validate_password("Abc!1234")
    assert valid is False
    assert any("more than 8 characters" in err for err in errors)

    # 9 characters with upper, lower, special
    valid, errors = validate_password("Abc!12345")
    assert valid is True
    assert len(errors) == 0


def test_password_validation_uppercase():
    """Password must contain at least one uppercase letter."""
    valid, errors = validate_password("lowercase#special123")
    assert valid is False
    assert any("uppercase" in err for err in errors)


def test_password_validation_lowercase():
    """Password must contain at least one lowercase letter."""
    valid, errors = validate_password("UPPERCASE#SPECIAL123")
    assert valid is False
    assert any("lowercase" in err for err in errors)


def test_password_validation_special_char():
    """Password must contain at least one special character."""
    valid, errors = validate_password("ValidPasswordWithoutSpecial123")
    assert valid is False
    assert any("special character" in err for err in errors)


def test_password_validation_valid():
    """Valid password meeting all criteria should pass."""
    valid, errors = validate_password("SubFlow#Secure2026!")
    assert valid is True
    assert len(errors) == 0


def test_email_validation():
    """Email validation helper check."""
    assert validate_email("valid.user@subflow.io") is True
    assert validate_email("invalid-email") is False
    assert validate_email("") is False
    assert validate_email(None) is False
