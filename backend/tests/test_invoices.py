import pytest
from datetime import date, timedelta
from decimal import Decimal
from backend.models import Customer, Product, Invoice
from backend.extensions import db


def test_create_invoice_success(client, admin_token, customer_user):
    """Test successful manual invoice creation by admin with Decimal calculations."""
    res = client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_user.customer_id,
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [
                {
                    "description": "Pro Tier Subscription",
                    "quantity": 2,
                    "unit_price": 50.00,
                    "discount_percent": 10.00
                },
                {
                    "description": "Extra Storage Add-on",
                    "quantity": 1,
                    "unit_price": 20.00,
                    "discount_percent": 0.00
                }
            ],
            "tax_amount": 5.00,
            "status": "draft"
        }
    )
    assert res.status_code == 201
    data = res.json["data"]
    assert data["invoice_number"].startswith("INV-")
    assert data["customer_id"] == customer_user.customer_id
    # Line 1: 2 * 50 * 0.9 = 90.00
    # Line 2: 1 * 20 = 20.00
    # Subtotal: 110.00
    # Total: 110.00 + 5.00 = 115.00
    assert data["subtotal"] == 110.00
    assert data["tax_amount"] == 5.00
    assert data["total_amount"] == 115.00
    assert data["balance_due"] == 115.00
    assert data["status"] == "draft"


def test_create_invoice_validation_negative_quantity(client, admin_token, customer_user):
    """Test that non-positive quantities are rejected."""
    res = client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_user.customer_id,
            "lines": [
                {
                    "description": "Invalid quantity item",
                    "quantity": -1,
                    "unit_price": 50.00
                }
            ]
        }
    )
    assert res.status_code == 422
    assert res.json["success"] is False


def test_issue_draft_invoice(client, admin_token, customer_user):
    """Test transitioning invoice from draft to posted (issued)."""
    create_res = client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_user.customer_id,
            "lines": [{"description": "Monthly Plan", "quantity": 1, "unit_price": 49.00}],
            "status": "draft"
        }
    )
    inv_id = create_res.json["data"]["id"]

    issue_res = client.post(
        f"/api/v1/invoices/{inv_id}/issue",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert issue_res.status_code == 200
    assert issue_res.json["data"]["status"] == "posted"


def test_cancel_invoice_success_and_forbidden_on_paid(client, admin_token, customer_user):
    """Test cancellation rules: unpaid draft can be cancelled, but paid cannot."""
    create_res = client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_user.customer_id,
            "lines": [{"description": "Service", "quantity": 1, "unit_price": 100.00}],
            "status": "draft"
        }
    )
    inv_id = create_res.json["data"]["id"]

    # Cancel unpaid draft
    cancel_res = client.post(
        f"/api/v1/invoices/{inv_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json["data"]["status"] == "cancelled"


def test_customer_cannot_view_other_customers_invoice(client, admin_token, customer_token, customer_user):
    """Test customer isolation (RBAC): customers cannot access another customer's invoice."""
    # Create a 2nd customer
    from backend.models import User
    second_user = User(
        email="other.customer@subflow.io",
        first_name="Other",
        last_name="Customer",
        role="customer"
    )
    second_user.set_password("SubFlow#Customer2026!")
    db.session.add(second_user)
    db.session.flush()

    second_customer = Customer(
        user_id=second_user.id,
        company_name="Second Corp",
        contact_name="Second Person",
        email=second_user.email
    )
    db.session.add(second_customer)
    db.session.commit()

    # Admin creates invoice for second customer
    res = client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": second_customer.id,
            "lines": [{"description": "Private consulting", "quantity": 1, "unit_price": 500.00}],
            "status": "posted"
        }
    )
    inv_id = res.json["data"]["id"]

    # Customer 1 attempts to read Customer 2's invoice
    get_res = client.get(
        f"/api/v1/invoices/{inv_id}",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert get_res.status_code == 403
    assert get_res.json["success"] is False


def test_customer_only_sees_own_invoices_in_list(client, admin_token, customer_token, customer_user):
    """Test customer invoice listing only returns invoices belonging to that customer."""
    # Create invoice for Customer 1
    client.post(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "customer_id": customer_user.customer_id,
            "lines": [{"description": "Item 1", "quantity": 1, "unit_price": 100.00}]
        }
    )

    list_res = client.get(
        "/api/v1/invoices",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert list_res.status_code == 200
    items = list_res.json["data"]["items"]
    assert len(items) >= 1
    for item in items:
        assert item["customer_id"] == customer_user.customer_id
