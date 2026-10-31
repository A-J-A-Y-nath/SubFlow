"""
Tests for Subscription lifecycle — Member 3
Covers: creation, state transitions, customer scoping, renewal.
"""
import pytest
from datetime import date, timedelta
from types import SimpleNamespace
from backend.extensions import db
from backend.models import User, Customer, Plan, Product, Subscription, SubscriptionLine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan(app, name="Test Plan", interval="monthly"):
    with app.app_context():
        plan = Plan(
            name=name,
            code=f"PLAN-{name.upper().replace(' ', '-')}",
            billing_interval=interval,
            billing_interval_count=1,
            base_price=99.00,
            is_active=True,
        )
        db.session.add(plan)
        db.session.commit()
        return plan.id


def _make_customer(app, user_id):
    with app.app_context():
        c = Customer(
            user_id=user_id,
            company_name="Test Corp",
            contact_name="Tester",
            email="tester@testcorp.io",
            payment_terms_days=30,
        )
        db.session.add(c)
        db.session.commit()
        return c.id


def _make_product(app):
    with app.app_context():
        p = Product(
            name="Test Product",
            sku="PROD-TEST-001",
            description="A test product",
            is_recurring=True,
            default_price=50.00,
        )
        db.session.add(p)
        db.session.commit()
        return p.id


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_subscription_success(client, app, admin_user, admin_token):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    prod_id = _make_product(app)

    res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id,
        "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [
            {"product_id": prod_id, "description": "Seat", "quantity": 1, "unit_price": 99.00}
        ],
    })
    assert res.status_code == 201, res.json
    data = res.json["data"]
    assert data["status"] == "draft"
    assert data["subscription_number"].startswith("SUB-")
    assert len(data["lines"]) == 1


def test_create_subscription_missing_plan(client, app, admin_token, admin_user):
    cust_id = _make_customer(app, admin_user.id)
    res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": 1, "description": "x", "quantity": 1, "unit_price": 10}],
    })
    assert res.status_code == 422
    assert res.json["error"]["code"] == "MISSING_FIELD"


def test_create_subscription_missing_lines(client, app, admin_token, admin_user):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id,
        "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [],
    })
    assert res.status_code == 422


def test_customer_cannot_create_subscription(client, app, customer_token, customer_user):
    res = client.post("/api/v1/subscriptions", headers=_auth_header(customer_token), json={
        "plan_id": 1, "customer_id": 1,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": 1, "description": "x", "quantity": 1, "unit_price": 10}],
    })
    assert res.status_code == 403


def test_status_transition_draft_to_active(client, app, admin_user, admin_token):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id, "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": prod_id, "description": "Seat", "quantity": 1, "unit_price": 50.00}],
    })
    sub_id = create_res.json["data"]["id"]

    patch_res = client.patch(f"/api/v1/subscriptions/{sub_id}/status",
                             headers=_auth_header(admin_token),
                             json={"status": "active"})
    assert patch_res.status_code == 200
    assert patch_res.json["data"]["status"] == "active"


def test_invalid_status_transition(client, app, admin_user, admin_token):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id, "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": prod_id, "description": "Seat", "quantity": 1, "unit_price": 50.00}],
    })
    sub_id = create_res.json["data"]["id"]

    # draft → paused is invalid
    patch_res = client.patch(f"/api/v1/subscriptions/{sub_id}/status",
                             headers=_auth_header(admin_token),
                             json={"status": "paused"})
    assert patch_res.status_code == 422
    assert patch_res.json["error"]["code"] == "INVALID_TRANSITION"


def test_customer_sees_only_own_subscriptions(client, app, admin_user, admin_token, customer_user, customer_token):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    prod_id = _make_product(app)

    # Create a subscription belonging to the admin's customer profile (not customer_user's)
    client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id, "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": prod_id, "description": "Seat", "quantity": 1, "unit_price": 50.00}],
    })

    # Customer user lists subscriptions — should be empty (their customer profile is linked to customer_user.id)
    list_res = client.get("/api/v1/subscriptions", headers=_auth_header(customer_token))
    assert list_res.status_code == 200
    assert list_res.json["data"]["items"] == []


def test_renew_subscription(client, app, admin_user, admin_token):
    plan_id = _make_plan(app)
    cust_id = _make_customer(app, admin_user.id)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/subscriptions", headers=_auth_header(admin_token), json={
        "plan_id": plan_id, "customer_id": cust_id,
        "start_date": date.today().isoformat(),
        "lines": [{"product_id": prod_id, "description": "Seat", "quantity": 1, "unit_price": 50.00}],
    })
    sub_id = create_res.json["data"]["id"]

    # Activate first
    client.patch(f"/api/v1/subscriptions/{sub_id}/status",
                 headers=_auth_header(admin_token), json={"status": "active"})

    # Renew
    renew_res = client.post(f"/api/v1/subscriptions/{sub_id}/renew",
                             headers=_auth_header(admin_token))
    assert renew_res.status_code == 200
    data = renew_res.json["data"]
    assert data["status"] == "active"
    # next_billing_date should have advanced
    assert data["next_billing_date"] is not None
