"""
Tests for Quotation workflow — Member 3
Covers: creation, update, send, confirm→subscription, validation, expired rejection.
"""
import pytest
from datetime import date, timedelta
from backend.extensions import db
from backend.models import User, Customer, Plan, Product


# ---------------------------------------------------------------------------
# Helpers (reusing the same pattern as test_subscriptions)
# ---------------------------------------------------------------------------

def _make_plan(app):
    with app.app_context():
        plan = Plan(
            name="Quo Test Plan",
            code="PLAN-QUO-TEST",
            billing_interval="monthly",
            billing_interval_count=1,
            base_price=99.00,
            is_active=True,
        )
        db.session.add(plan)
        db.session.commit()
        return plan.id


def _make_customer(app, user_id=None):
    with app.app_context():
        c = Customer(
            user_id=user_id,
            company_name="Quo Test Corp",
            contact_name="Tester",
            email="quo@testcorp.io",
            payment_terms_days=30,
        )
        db.session.add(c)
        db.session.commit()
        return c.id


def _make_product(app):
    with app.app_context():
        p = Product(
            name="Quo Product",
            sku="PROD-QUO-001",
            description="Quotation product",
            is_recurring=True,
            default_price=50.00,
        )
        db.session.add(p)
        db.session.commit()
        return p.id


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _valid_quotation_payload(customer_id, plan_id, product_id, days_valid=30):
    today = date.today()
    return {
        "customer_id": customer_id,
        "plan_id": plan_id,
        "issue_date": today.isoformat(),
        "valid_until": (today + timedelta(days=days_valid)).isoformat(),
        "lines": [
            {
                "product_id": product_id,
                "description": "Seat License",
                "quantity": 2,
                "unit_price": 99.00,
                "discount_percent": 10,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_quotation_success(client, app, admin_user, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)

    res = client.post("/api/v1/quotations", headers=_auth(admin_token),
                      json=_valid_quotation_payload(cust_id, plan_id, prod_id))
    assert res.status_code == 201, res.json
    data = res.json["data"]
    assert data["status"] == "draft"
    assert data["quotation_number"].startswith("QUO-")
    # Totals: 2 * 99 = 198, 10% disc = 19.80, taxable = 178.20, 18% GST = 32.076, total ≈ 210.28
    assert data["total_amount"] > 0


def test_create_quotation_missing_customer(client, app, admin_token):
    res = client.post("/api/v1/quotations", headers=_auth(admin_token), json={
        "issue_date": date.today().isoformat(),
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
        "lines": [{"product_id": 1, "description": "x", "quantity": 1, "unit_price": 10}],
    })
    assert res.status_code == 422
    assert res.json["error"]["code"] == "MISSING_FIELD"


def test_create_quotation_invalid_date_range(client, app, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)
    today = date.today()
    res = client.post("/api/v1/quotations", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "plan_id": plan_id,
        "issue_date": today.isoformat(),
        "valid_until": today.isoformat(),  # same day — invalid
        "lines": [{"product_id": prod_id, "description": "x", "quantity": 1, "unit_price": 10}],
    })
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_DATE_RANGE"


def test_send_quotation(client, app, admin_user, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/quotations", headers=_auth(admin_token),
                              json=_valid_quotation_payload(cust_id, plan_id, prod_id))
    quo_id = create_res.json["data"]["id"]

    send_res = client.post(f"/api/v1/quotations/{quo_id}/send", headers=_auth(admin_token))
    assert send_res.status_code == 200
    assert send_res.json["data"]["status"] == "sent"


def test_confirm_quotation_creates_subscription(client, app, admin_user, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/quotations", headers=_auth(admin_token),
                              json=_valid_quotation_payload(cust_id, plan_id, prod_id))
    quo_id = create_res.json["data"]["id"]

    confirm_res = client.post(f"/api/v1/quotations/{quo_id}/confirm",
                               headers=_auth(admin_token),
                               json={"start_date": date.today().isoformat()})
    assert confirm_res.status_code == 201, confirm_res.json
    result = confirm_res.json["data"]
    assert result["quotation"]["status"] == "approved"
    assert result["subscription"]["status"] == "draft"
    assert result["subscription"]["plan_id"] == plan_id
    assert result["subscription"]["customer_id"] == cust_id


def test_confirm_already_approved_quotation_fails(client, app, admin_user, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)

    create_res = client.post("/api/v1/quotations", headers=_auth(admin_token),
                              json=_valid_quotation_payload(cust_id, plan_id, prod_id))
    quo_id = create_res.json["data"]["id"]

    # Confirm once
    client.post(f"/api/v1/quotations/{quo_id}/confirm", headers=_auth(admin_token),
                json={"start_date": date.today().isoformat()})

    # Try to confirm again — should fail
    second_res = client.post(f"/api/v1/quotations/{quo_id}/confirm", headers=_auth(admin_token),
                              json={"start_date": date.today().isoformat()})
    assert second_res.status_code == 422


def test_confirm_expired_quotation_fails(client, app, admin_user, admin_token):
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)
    today = date.today()

    res = client.post("/api/v1/quotations", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "plan_id": plan_id,
        "issue_date": (today - timedelta(days=60)).isoformat(),
        "valid_until": (today - timedelta(days=1)).isoformat(),  # already expired
        "lines": [{"product_id": prod_id, "description": "x", "quantity": 1, "unit_price": 50}],
    })
    quo_id = res.json["data"]["id"]

    confirm_res = client.post(f"/api/v1/quotations/{quo_id}/confirm", headers=_auth(admin_token),
                               json={"start_date": today.isoformat()})
    assert confirm_res.status_code == 422
    assert confirm_res.json["error"]["code"] == "QUOTATION_EXPIRED"


def test_customer_cannot_access_quotations(client, customer_token):
    res = client.get("/api/v1/quotations", headers=_auth(customer_token))
    assert res.status_code == 403


def test_quotation_totals_accuracy(client, app, admin_user, admin_token):
    """Verify subtotal, discount, tax, and total are computed correctly."""
    cust_id = _make_customer(app)
    plan_id = _make_plan(app)
    prod_id = _make_product(app)

    res = client.post("/api/v1/quotations", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "plan_id": plan_id,
        "issue_date": date.today().isoformat(),
        "valid_until": (date.today() + timedelta(days=30)).isoformat(),
        "lines": [
            {"product_id": prod_id, "description": "Item", "quantity": 1, "unit_price": 100.00, "discount_percent": 0},
        ],
    })
    data = res.json["data"]
    # 100 - 0 disc = 100, * 1.18 GST = 118.00
    assert data["subtotal"] == pytest.approx(100.00, abs=0.01)
    assert data["discount_amount"] == pytest.approx(0.00, abs=0.01)
    assert data["tax_amount"] == pytest.approx(18.00, abs=0.01)
    assert data["total_amount"] == pytest.approx(118.00, abs=0.01)
