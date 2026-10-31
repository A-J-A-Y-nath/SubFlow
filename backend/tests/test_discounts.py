import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from backend.models import DiscountRule
from backend.services.discount_service import DiscountService
from backend.extensions import db


def test_percentage_discount_calculation(app_context):
    """Test 20% discount calculation with min order threshold and max discount cap."""
    rule = DiscountRule(
        code="SAVE20",
        name="Save 20 Percent",
        discount_type="percentage",
        value=Decimal("20.00"),
        min_order_amount=Decimal("50.00"),
        max_discount_amount=Decimal("30.00"),
        is_active=True
    )
    db.session.add(rule)
    db.session.commit()

    # Case 1: Order amount < min_order (40.00 < 50.00) -> invalid
    valid, disc, _, err = DiscountService.validate_and_calculate_discount("SAVE20", Decimal("40.00"))
    assert valid is False
    assert "Minimum qualifying" in err

    # Case 2: Order amount 100.00 -> 20% is 20.00 (< 30.00 cap)
    valid, disc, _, _ = DiscountService.validate_and_calculate_discount("SAVE20", Decimal("100.00"))
    assert valid is True
    assert disc == Decimal("20.00")

    # Case 3: Order amount 200.00 -> 20% is 40.00, but capped at 30.00
    valid, disc, _, _ = DiscountService.validate_and_calculate_discount("SAVE20", Decimal("200.00"))
    assert valid is True
    assert disc == Decimal("30.00")


def test_fixed_discount_calculation(app_context):
    """Test fixed discount reduction capped at total order amount."""
    rule = DiscountRule(
        code="FLAT50",
        name="Flat $50 Off",
        discount_type="fixed",
        value=Decimal("50.00"),
        min_order_amount=Decimal("20.00"),
        is_active=True
    )
    db.session.add(rule)
    db.session.commit()

    # Order of $100 -> $50 off
    valid, disc, _, _ = DiscountService.validate_and_calculate_discount("FLAT50", Decimal("100.00"))
    assert valid is True
    assert disc == Decimal("50.00")

    # Order of $30 -> capped so final amount is not negative ($30 discount)
    valid, disc, _, _ = DiscountService.validate_and_calculate_discount("FLAT50", Decimal("30.00"))
    assert valid is True
    assert disc == Decimal("30.00")


def test_expired_and_inactive_discount(app_context):
    """Test that expired coupons or inactive rules are rejected."""
    now = datetime.now(timezone.utc)
    expired = DiscountRule(
        code="EXPIRED10",
        name="Expired",
        discount_type="fixed",
        value=Decimal("10.00"),
        valid_to=now - timedelta(days=2),
        is_active=True
    )
    inactive = DiscountRule(
        code="INACTIVE10",
        name="Inactive",
        discount_type="fixed",
        value=Decimal("10.00"),
        is_active=False
    )
    db.session.add_all([expired, inactive])
    db.session.commit()

    valid, _, _, err = DiscountService.validate_and_calculate_discount("EXPIRED10", Decimal("50.00"))
    assert valid is False
    assert "expired" in err.lower()

    valid, _, _, err = DiscountService.validate_and_calculate_discount("INACTIVE10", Decimal("50.00"))
    assert valid is False
    assert "deactivated" in err.lower()


def test_usage_limit_exhausted(app_context):
    """Test that coupon reaching max_uses cannot be redeemed."""
    rule = DiscountRule(
        code="LIMITED3",
        name="Limited 3 Uses",
        discount_type="fixed",
        value=Decimal("15.00"),
        max_uses=2,
        current_uses=2,
        is_active=True
    )
    db.session.add(rule)
    db.session.commit()

    valid, _, _, err = DiscountService.validate_and_calculate_discount("LIMITED3", Decimal("100.00"))
    assert valid is False
    assert "maximum redemption limit" in err.lower()


def test_discount_api_endpoints(client, admin_token):
    """Test discount CRUD and validate endpoints via REST API."""
    create_res = client.post(
        "/api/v1/discounts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "code": "PROMO2026",
            "name": "Promo 2026",
            "discount_type": "percentage",
            "value": 15.0,
            "min_order_amount": 25.0,
            "max_uses": 100
        }
    )
    assert create_res.status_code == 201
    assert create_res.json["data"]["code"] == "PROMO2026"

    # Validate endpoint
    val_res = client.get(
        "/api/v1/discounts/validate/PROMO2026?amount=100",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert val_res.status_code == 200
    assert val_res.json["data"]["calculated_discount"] == 15.0

    # Toggle status endpoint
    disc_id = create_res.json["data"]["id"]
    tog_res = client.post(
        f"/api/v1/discounts/{disc_id}/toggle-status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert tog_res.status_code == 200
    assert tog_res.json["data"]["is_active"] is False
