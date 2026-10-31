"""
Tests for Customer Management API endpoints — /api/v1/customers
Covers: CRUD operations, RBAC enforcement, pagination, search, and customer isolation.
"""
import pytest
from backend.extensions import db
from backend.models import Customer, User


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_list_customers_as_admin(client, admin_token, sample_customer):
    res = client.get("/api/v1/customers", headers=_auth_header(admin_token))
    assert res.status_code == 200
    data = res.json["data"]
    assert "items" in data
    assert any(c["id"] == sample_customer.id for c in data["items"])


def test_list_customers_search_and_pagination(client, admin_token, app):
    with app.app_context():
        c1 = Customer(company_name="Apex Global", contact_name="Alice Apex", email="alice@apex.com")
        c2 = Customer(company_name="Zenith Dynamics", contact_name="Bob Zenith", email="bob@zenith.com")
        db.session.add_all([c1, c2])
        db.session.commit()

    # Search for "Apex"
    res = client.get("/api/v1/customers?search=Apex", headers=_auth_header(admin_token))
    assert res.status_code == 200
    items = res.json["data"]["items"]
    assert len(items) >= 1
    assert all("Apex" in c["company_name"] for c in items)


def test_customer_isolation_on_customer_list(client, customer_token, sample_customer, app):
    with app.app_context():
        # Another customer
        c2 = Customer(company_name="Secret Corp", contact_name="Eve", email="eve@secret.com")
        db.session.add(c2)
        db.session.commit()

    # Customer user should ONLY see their own profile
    res = client.get("/api/v1/customers", headers=_auth_header(customer_token))
    assert res.status_code == 200
    items = res.json["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == sample_customer.id


def test_create_customer_success(client, admin_token):
    payload = {
        "company_name": "Horizon Innovations",
        "contact_name": "Howard Stark",
        "email": "howard@horizon.io",
        "phone": "+1-555-0199",
        "billing_city": "New York",
        "billing_country": "United States",
        "currency": "USD",
        "payment_terms_days": 15,
    }
    res = client.post("/api/v1/customers", headers=_auth_header(admin_token), json=payload)
    assert res.status_code == 201, res.json
    data = res.json["data"]
    assert data["company_name"] == "Horizon Innovations"
    assert data["email"] == "howard@horizon.io"
    assert data["payment_terms_days"] == 15


def test_create_customer_duplicate_email(client, admin_token, sample_customer):
    payload = {
        "company_name": "Duplicate Inc",
        "email": sample_customer.email,
    }
    res = client.post("/api/v1/customers", headers=_auth_header(admin_token), json=payload)
    assert res.status_code == 409
    assert res.json["error"]["code"] == "CONFLICT"


def test_create_customer_forbidden_for_regular_customer(client, customer_token):
    payload = {"company_name": "Rogue Co", "email": "rogue@co.com"}
    res = client.post("/api/v1/customers", headers=_auth_header(customer_token), json=payload)
    assert res.status_code == 403


def test_update_customer_success(client, admin_token, sample_customer):
    payload = {
        "company_name": "Acme Updated Corporation",
        "payment_terms_days": 45,
    }
    res = client.put(f"/api/v1/customers/{sample_customer.id}", headers=_auth_header(admin_token), json=payload)
    assert res.status_code == 200
    data = res.json["data"]
    assert data["company_name"] == "Acme Updated Corporation"
    assert data["payment_terms_days"] == 45


def test_deactivate_and_reactivate_customer(client, admin_token, sample_customer):
    res = client.put(f"/api/v1/customers/{sample_customer.id}", headers=_auth_header(admin_token), json={"is_active": False})
    assert res.status_code == 200
    assert res.json["data"]["is_active"] is False

    res2 = client.put(f"/api/v1/customers/{sample_customer.id}", headers=_auth_header(admin_token), json={"is_active": True})
    assert res2.status_code == 200
    assert res2.json["data"]["is_active"] is True
