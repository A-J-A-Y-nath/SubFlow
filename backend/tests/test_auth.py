import pytest
from backend.models import User


def test_registration_success(client):
    """Test successful user registration."""
    res = client.post("/api/v1/auth/register", json={
        "email": "new.user@subflow.io",
        "password": "StrongPassword#2026",
        "first_name": "New",
        "last_name": "User",
        "company_name": "New Ventures Inc"
    })
    assert res.status_code == 201
    data = res.json
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "new.user@subflow.io"


def test_registration_invalid_password(client):
    """Test registration fails with weak password."""
    res = client.post("/api/v1/auth/register", json={
        "email": "weak@subflow.io",
        "password": "weak",
        "first_name": "Weak",
        "last_name": "Password"
    })
    assert res.status_code == 422
    data = res.json
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_PASSWORD"


def test_registration_duplicate_email(client, customer_user):
    """Test registration with existing email returns 409 conflict."""
    res = client.post("/api/v1/auth/register", json={
        "email": customer_user.email,
        "password": "ValidPassword#2026",
        "first_name": "Duplicate",
        "last_name": "User"
    })
    assert res.status_code == 409
    assert res.json["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_success(client, customer_user):
    """Test successful login returns tokens and user object."""
    res = client.post("/api/v1/auth/login", json={
        "email": customer_user.email,
        "password": "SubFlow#Customer2026!"
    })
    assert res.status_code == 200
    assert res.json["success"] is True
    assert "access_token" in res.json["data"]
    assert res.json["data"]["user"]["email"] == customer_user.email


def test_login_invalid_password(client, customer_user):
    """Test login with wrong password returns 401."""
    res = client.post("/api/v1/auth/login", json={
        "email": customer_user.email,
        "password": "WrongPassword#2026"
    })
    assert res.status_code == 401
    assert res.json["error"]["code"] == "INVALID_CREDENTIALS"


def test_current_user_me_endpoint(client, customer_token):
    """Test /api/v1/auth/me returns authenticated user details."""
    res = client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {customer_token}"
    })
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["email"] == "customer.test@subflow.io"


def test_unauthenticated_me_endpoint(client):
    """Test accessing protected /me without token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json["success"] is False


def test_admin_can_create_staff(client, admin_token):
    """Admin can create a staff account."""
    res = client.post("/api/v1/auth/create-staff", headers={
        "Authorization": f"Bearer {admin_token}"
    }, json={
        "email": "new.staff@subflow.io",
        "password": "StaffPassword#2026",
        "first_name": "Jane",
        "last_name": "Staff"
    })
    assert res.status_code == 201
    assert res.json["success"] is True
    assert res.json["data"]["role"] == "staff"


def test_customer_cannot_create_staff(client, customer_token):
    """Non-admin customer attempting to create staff receives 403 Forbidden."""
    res = client.post("/api/v1/auth/create-staff", headers={
        "Authorization": f"Bearer {customer_token}"
    }, json={
        "email": "unauthorized.staff@subflow.io",
        "password": "StaffPassword#2026",
        "first_name": "Bad",
        "last_name": "Actor"
    })
    assert res.status_code == 403
    assert res.json["error"]["code"] == "FORBIDDEN"
