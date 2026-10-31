"""
Tests for password reset and password change endpoints in /api/v1/auth
"""
import pytest
from backend.models import User


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_reset_password_success(client, app, admin_user):
    new_pwd = "NewSecurePassword#2026"
    res = client.post("/api/v1/auth/reset-password", json={
        "email": admin_user.email,
        "new_password": new_pwd,
    })
    assert res.status_code == 200
    assert "Password reset successfully" in res.json["message"]

    # Verify user can log in with new password
    login_res = client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": new_pwd,
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json["data"]


def test_reset_password_invalid_complexity(client, admin_user):
    res = client.post("/api/v1/auth/reset-password", json={
        "email": admin_user.email,
        "new_password": "weak",
    })
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_PASSWORD"


def test_reset_password_unknown_email(client):
    res = client.post("/api/v1/auth/reset-password", json={
        "email": "nonexistent_subflow_user@example.com",
        "new_password": "ValidPassword#123",
    })
    assert res.status_code == 404
    assert res.json["error"]["code"] == "USER_NOT_FOUND"


def test_change_password_authenticated(client, customer_token, customer_user):
    new_pwd = "CustomerNewPassword#2026"
    res = client.post("/api/v1/auth/change-password", headers=_auth_header(customer_token), json={
        "old_password": customer_user.password,
        "new_password": new_pwd,
    })
    assert res.status_code == 200

    # Verify login with new password
    login_res = client.post("/api/v1/auth/login", json={
        "email": customer_user.email,
        "password": new_pwd,
    })
    assert login_res.status_code == 200


def test_change_password_wrong_old_password(client, customer_token):
    res = client.post("/api/v1/auth/change-password", headers=_auth_header(customer_token), json={
        "old_password": "WrongPassword999!",
        "new_password": "NewValidPassword#2026",
    })
    assert res.status_code == 401
    assert res.json["error"]["code"] == "INVALID_OLD_PASSWORD"
