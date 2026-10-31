"""
Tests for Invoice lifecycle — Member 3
Covers: creation, confirm, cancel, cannot cancel paid, total accuracy, customer scoping.
"""
import pytest
from datetime import date, timedelta
from backend.extensions import db
from backend.models import Customer, Plan, Product, Subscription, SubscriptionLine, Invoice, InvoiceLine


def _make_customer(app):
    with app.app_context():
        c = Customer(
            company_name="Invoice Test Corp",
            contact_name="Inv Tester",
            email="inv@testcorp.io",
            payment_terms_days=30,
        )
        db.session.add(c)
        db.session.commit()
        return c.id


def _make_product(app):
    with app.app_context():
        p = Product(
            name="Invoice Product",
            sku="PROD-INV-001",
            description="Invoice product",
            is_recurring=True,
            default_price=100.00,
        )
        db.session.add(p)
        db.session.commit()
        return p.id


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _manual_invoice_payload(customer_id, product_id):
    today = date.today()
    return {
        "customer_id": customer_id,
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "lines": [
            {"product_id": product_id, "description": "Service Fee", "quantity": 1, "unit_price": 100.00, "discount_percent": 0},
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_invoice_success(client, app, admin_token):
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    res = client.post("/api/v1/invoices", headers=_auth(admin_token),
                      json=_manual_invoice_payload(cust_id, prod_id))
    assert res.status_code == 201, res.json
    data = res.json["data"]
    assert data["status"] == "draft"
    assert data["invoice_number"].startswith("INV-")


def test_create_invoice_missing_due_date(client, app, admin_token):
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    res = client.post("/api/v1/invoices", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "invoice_date": date.today().isoformat(),
        "lines": [{"product_id": prod_id, "description": "x", "quantity": 1, "unit_price": 10}],
    })
    assert res.status_code == 422


def test_confirm_invoice(client, app, admin_token):
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    create_res = client.post("/api/v1/invoices", headers=_auth(admin_token),
                             json=_manual_invoice_payload(cust_id, prod_id))
    inv_id = create_res.json["data"]["id"]

    confirm_res = client.post(f"/api/v1/invoices/{inv_id}/confirm", headers=_auth(admin_token))
    assert confirm_res.status_code == 200
    assert confirm_res.json["data"]["status"] == "posted"


def test_cancel_draft_invoice(client, app, admin_token):
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    create_res = client.post("/api/v1/invoices", headers=_auth(admin_token),
                             json=_manual_invoice_payload(cust_id, prod_id))
    inv_id = create_res.json["data"]["id"]

    cancel_res = client.post(f"/api/v1/invoices/{inv_id}/cancel", headers=_auth(admin_token))
    assert cancel_res.status_code == 200
    assert cancel_res.json["data"]["status"] == "cancelled"


def test_cannot_cancel_paid_invoice(app, client, admin_token):
    """Directly insert a paid invoice and verify it cannot be cancelled via API."""
    cust_id = _make_customer(app)
    prod_id = _make_product(app)

    with app.app_context():
        today = date.today()
        inv = Invoice(
            invoice_number="INV-PAID-TEST",
            customer_id=cust_id,
            status="paid",
            invoice_date=today,
            due_date=today + timedelta(days=30),
            total_amount=118.00,
            amount_paid=118.00,
            balance_due=0.00,
            currency="USD",
        )
        db.session.add(inv)
        db.session.commit()
        inv_id = inv.id

    cancel_res = client.post(f"/api/v1/invoices/{inv_id}/cancel", headers=_auth(admin_token))
    assert cancel_res.status_code == 422
    assert cancel_res.json["error"]["code"] == "INVALID_STATUS"


def test_invoice_totals_accuracy(client, app, admin_token):
    """Totals: 1 * 200 - 0% disc = 200 taxable, 18% GST = 36, total = 236."""
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    today = date.today()
    res = client.post("/api/v1/invoices", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "lines": [{"product_id": prod_id, "description": "Service", "quantity": 2, "unit_price": 100.00, "discount_percent": 0}],
    })
    data = res.json["data"]
    assert data["subtotal"] == pytest.approx(200.00, abs=0.01)
    assert data["tax_amount"] == pytest.approx(36.00, abs=0.01)
    assert data["total_amount"] == pytest.approx(236.00, abs=0.01)
    assert data["balance_due"] == pytest.approx(236.00, abs=0.01)


def test_invoice_with_discount_totals(client, app, admin_token):
    """Totals: 1 * 100 - 20% disc = 80 taxable, 18% GST = 14.40, total = 94.40."""
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    today = date.today()
    res = client.post("/api/v1/invoices", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "lines": [{"product_id": prod_id, "description": "Service", "quantity": 1, "unit_price": 100.00, "discount_percent": 20}],
    })
    data = res.json["data"]
    assert data["discount_amount"] == pytest.approx(20.00, abs=0.01)
    assert data["tax_amount"] == pytest.approx(14.40, abs=0.01)
    assert data["total_amount"] == pytest.approx(94.40, abs=0.01)


def test_customer_sees_only_own_invoices(client, app, customer_user, customer_token, admin_token):
    """Customer can list invoices but only sees their own."""
    cust_id = _make_customer(app)
    prod_id = _make_product(app)

    # Create invoice for a different customer (not customer_user's linked profile)
    today = date.today()
    client.post("/api/v1/invoices", headers=_auth(admin_token), json={
        "customer_id": cust_id,
        "invoice_date": today.isoformat(),
        "due_date": (today + timedelta(days=30)).isoformat(),
        "lines": [{"product_id": prod_id, "description": "x", "quantity": 1, "unit_price": 10}],
    })

    list_res = client.get("/api/v1/invoices", headers=_auth(customer_token))
    assert list_res.status_code == 200
    assert list_res.json["data"]["items"] == []


def test_customer_cannot_create_invoice(client, customer_token):
    res = client.post("/api/v1/invoices", headers=_auth(customer_token), json={})
    assert res.status_code == 403


def test_confirm_already_posted_invoice_fails(client, app, admin_token):
    cust_id = _make_customer(app)
    prod_id = _make_product(app)
    create_res = client.post("/api/v1/invoices", headers=_auth(admin_token),
                             json=_manual_invoice_payload(cust_id, prod_id))
    inv_id = create_res.json["data"]["id"]

    client.post(f"/api/v1/invoices/{inv_id}/confirm", headers=_auth(admin_token))
    second_confirm = client.post(f"/api/v1/invoices/{inv_id}/confirm", headers=_auth(admin_token))
    assert second_confirm.status_code == 422
    assert second_confirm.json["error"]["code"] == "INVALID_STATUS"
