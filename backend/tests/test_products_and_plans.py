import pytest
from datetime import date, timedelta
from decimal import Decimal
from backend.models.product import Product, ProductVariant
from backend.models.plan import Plan


# ============================================================================
# Product Management Tests
# ============================================================================

def test_create_product_success_admin(client, admin_token):
    """Admin can create a new product."""
    payload = {
        "name": "Cloud Enterprise Storage",
        "sku": "PROD-STORAGE-ENT",
        "description": "High performance block storage",
        "default_price": 49.99,
        "currency": "USD",
        "unit_of_measure": "GB",
        "is_recurring": True,
        "is_active": True,
    }
    res = client.post(
        "/api/v1/products",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json["data"]
    assert data["name"] == "Cloud Enterprise Storage"
    assert data["sku"] == "PROD-STORAGE-ENT"
    assert data["default_price"] == 49.99
    assert data["currency"] == "USD"
    assert data["is_active"] is True
    assert data["is_recurring"] is True


def test_create_product_success_staff(client, staff_token):
    """Staff member can create a new product."""
    payload = {
        "name": "Consulting Hour",
        "sku": "PROD-CONSULT-HR",
        "default_price": 150.00,
        "is_recurring": False,
    }
    res = client.post(
        "/api/v1/products",
        json=payload,
        headers={"Authorization": f"Bearer {staff_token}"},
    )
    assert res.status_code == 201
    assert res.json["data"]["sku"] == "PROD-CONSULT-HR"
    assert res.json["data"]["is_recurring"] is False


def test_create_product_forbidden_customer(client, customer_token):
    """Customer is rejected with 403 Forbidden when trying to create products."""
    payload = {
        "name": "Customer Created Product",
        "sku": "PROD-HACK-01",
        "default_price": 10.00,
    }
    res = client.post(
        "/api/v1/products",
        json=payload,
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert res.status_code == 403
    assert res.json["error"]["code"] == "FORBIDDEN"


def test_create_product_unauthorized(client):
    """Unauthenticated requests are rejected with 401."""
    res = client.post("/api/v1/products", json={"name": "Test", "sku": "T1", "default_price": 10})
    assert res.status_code == 401


def test_create_product_missing_required_fields(client, admin_token):
    """Missing name or SKU results in 400 Bad Request."""
    res_no_name = client.post(
        "/api/v1/products",
        json={"sku": "PROD-NONAME", "default_price": 10.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_no_name.status_code == 400
    assert res_no_name.json["error"]["code"] == "MISSING_NAME"

    res_no_sku = client.post(
        "/api/v1/products",
        json={"name": "Valid Name", "default_price": 10.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_no_sku.status_code == 400
    assert res_no_sku.json["error"]["code"] == "MISSING_SKU"


def test_create_product_duplicate_sku(client, admin_token):
    """Duplicate product SKU returns 409 Conflict."""
    payload = {"name": "Unique Product", "sku": "PROD-DUPE-CHECK", "default_price": 25.00}
    res1 = client.post("/api/v1/products", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res1.status_code == 201

    res2 = client.post("/api/v1/products", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res2.status_code == 409
    assert res2.json["error"]["code"] == "DUPLICATE_SKU"


def test_create_product_invalid_price(client, admin_token):
    """Negative prices and non-numeric values return 422 Unprocessable Entity."""
    # Negative price
    res_neg = client.post(
        "/api/v1/products",
        json={"name": "Bad Price", "sku": "PROD-NEG", "default_price": -15.50},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_neg.status_code == 422
    assert res_neg.json["error"]["code"] == "INVALID_PRICE"

    # Non-numeric price
    res_nan = client.post(
        "/api/v1/products",
        json={"name": "Bad Price", "sku": "PROD-NAN", "default_price": "invalid_number"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_nan.status_code == 422
    assert res_nan.json["error"]["code"] == "INVALID_PRICE"


def test_list_products_and_search(client, admin_token):
    """List products with search filter and pagination."""
    # Seed 2 products
    client.post(
        "/api/v1/products",
        json={"name": "Alpha Service", "sku": "PROD-ALPHA", "default_price": 10.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    client.post(
        "/api/v1/products",
        json={"name": "Beta Addon", "sku": "PROD-BETA", "default_price": 20.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Search for Alpha
    res = client.get("/api/v1/products?search=Alpha", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    items = res.json["data"]["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "PROD-ALPHA"

    # Search by SKU
    res_sku = client.get("/api/v1/products?search=BETA", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_sku.status_code == 200
    assert len(res_sku.json["data"]["items"]) == 1
    assert res_sku.json["data"]["items"][0]["sku"] == "PROD-BETA"


def test_customer_cannot_view_inactive_products(client, admin_token, customer_token):
    """Customers are restricted to active products only."""
    # Create an inactive product
    res_create = client.post(
        "/api/v1/products",
        json={"name": "Secret Retired Product", "sku": "PROD-RETIRED", "default_price": 5.00, "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_create.status_code == 201
    prod_id = res_create.json["data"]["id"]

    # Customer list should not include it
    res_list = client.get("/api/v1/products", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_list.status_code == 200
    skus = [p["sku"] for p in res_list.json["data"]["items"]]
    assert "PROD-RETIRED" not in skus

    # Direct detail GET should return 404 for customer
    res_get = client.get(f"/api/v1/products/{prod_id}", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_get.status_code == 404

    # Staff/Admin can view it
    res_admin = client.get(f"/api/v1/products/{prod_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    assert res_admin.json["data"]["is_active"] is False


def test_update_product_and_toggle_status(client, admin_token):
    """Test updating product fields and toggling active status."""
    res_create = client.post(
        "/api/v1/products",
        json={"name": "Initial Name", "sku": "PROD-UPDATE-TEST", "default_price": 100.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod_id = res_create.json["data"]["id"]

    # Update product
    res_update = client.put(
        f"/api/v1/products/{prod_id}",
        json={"name": "Updated Name", "default_price": 125.50, "description": "Updated desc"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json["data"]["name"] == "Updated Name"
    assert res_update.json["data"]["default_price"] == 125.50
    assert res_update.json["data"]["description"] == "Updated desc"

    # Toggle status to inactive
    res_status = client.patch(
        f"/api/v1/products/{prod_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_status.status_code == 200
    assert res_status.json["data"]["is_active"] is False


# ============================================================================
# Product Variant Tests
# ============================================================================

def test_variant_pricing_calculation(client, admin_token):
    """
    Verify exact requirement:
    Base product price: ₹2,000
    Selected variant additional price: ₹560
    Final price: ₹2,560
    Formula: Final unit price = Base product price + Variant additional price.
    Uses Decimal/Numeric arithmetic.
    """
    # 1. Create base product with base price = 2000.00
    prod_res = client.post(
        "/api/v1/products",
        json={"name": "Hosting Server", "sku": "PROD-HOST-SRV", "default_price": 2000.00, "currency": "INR"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json["data"]["id"]

    # 2. Add variant with additional price = 560.00
    var_res = client.post(
        f"/api/v1/products/{prod_id}/variants",
        json={
            "name": "Dedicated IPv4 & RAM Boost",
            "sku": "VAR-HOST-BOOST",
            "price_extra": 560.00,
            "description": "Adds 8GB extra RAM and 1 Dedicated IP",
            "attributes": {"ram": "8GB", "ip_type": "dedicated"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert var_res.status_code == 201
    var_data = var_res.json["data"]
    assert var_data["base_price"] == 2000.00
    assert var_data["price_extra"] == 560.00
    assert var_data["final_price"] == 2560.00
    assert var_data["description"] == "Adds 8GB extra RAM and 1 Dedicated IP"
    assert var_data["attributes"]["ram"] == "8GB"


def test_variant_negative_price_rejected(client, admin_token):
    """Reject negative variant price_extra with 422."""
    prod_res = client.post(
        "/api/v1/products",
        json={"name": "Base Item", "sku": "PROD-BASE-ITEM", "default_price": 100.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod_id = prod_res.json["data"]["id"]

    res = client.post(
        f"/api/v1/products/{prod_id}/variants",
        json={"name": "Negative Addon", "sku": "VAR-NEG-ADDON", "price_extra": -50.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_PRICE"


def test_variant_duplicate_sku_rejected(client, admin_token):
    """Reject duplicate variant SKU with 409 Conflict."""
    prod_res = client.post(
        "/api/v1/products",
        json={"name": "Gadget", "sku": "PROD-GADGET-01", "default_price": 50.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod_id = prod_res.json["data"]["id"]

    v1 = client.post(
        f"/api/v1/products/{prod_id}/variants",
        json={"name": "Red", "sku": "VAR-GADGET-RED", "price_extra": 5.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert v1.status_code == 201

    v2 = client.post(
        f"/api/v1/products/{prod_id}/variants",
        json={"name": "Crimson", "sku": "VAR-GADGET-RED", "price_extra": 6.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert v2.status_code == 409
    assert v2.json["error"]["code"] == "DUPLICATE_SKU"


def test_variant_crud_and_status_toggle(client, admin_token):
    """Test full variant lifecycle: list, get, update, toggle status, delete."""
    prod_res = client.post(
        "/api/v1/products",
        json={"name": "T-Shirt", "sku": "PROD-TSHIRT", "default_price": 20.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    prod_id = prod_res.json["data"]["id"]

    # Create variant
    var_res = client.post(
        f"/api/v1/products/{prod_id}/variants",
        json={"name": "Size L", "sku": "VAR-TSHIRT-L", "price_extra": 2.50},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    var_id = var_res.json["data"]["id"]

    # List variants
    list_res = client.get(f"/api/v1/products/{prod_id}/variants", headers={"Authorization": f"Bearer {admin_token}"})
    assert list_res.status_code == 200
    assert len(list_res.json["data"]["items"]) == 1

    # Update variant
    up_res = client.put(
        f"/api/v1/products/{prod_id}/variants/{var_id}",
        json={"name": "Size XL", "price_extra": 4.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert up_res.status_code == 200
    assert up_res.json["data"]["name"] == "Size XL"
    assert up_res.json["data"]["final_price"] == 24.00

    # Toggle status
    stat_res = client.patch(
        f"/api/v1/products/{prod_id}/variants/{var_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert stat_res.status_code == 200
    assert stat_res.json["data"]["is_active"] is False

    # Delete variant
    del_res = client.delete(
        f"/api/v1/products/{prod_id}/variants/{var_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert del_res.status_code == 200


# ============================================================================
# Subscription Plan Tests
# ============================================================================

def test_create_plan_success(client, admin_token):
    """Admin can create a valid subscription plan with all supported fields."""
    today = date.today()
    next_year = today + timedelta(days=365)

    payload = {
        "name": "Team Growth",
        "code": "PLAN-TEAM-GROWTH-MO",
        "description": "Designed for expanding teams requiring high throughput",
        "billing_interval": "monthly",
        "billing_interval_count": 1,
        "base_price": 79.00,
        "setup_fee": 25.00,
        "currency": "USD",
        "trial_days": 14,
        "min_quantity": 3,
        "available_from": today.isoformat(),
        "available_until": next_year.isoformat(),
        "auto_renew": True,
        "features": ["15 Team Members", "Automated Billing", "Email Support", "API Access"],
        "is_active": True,
    }

    res = client.post(
        "/api/v1/plans",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json["data"]
    assert data["name"] == "Team Growth"
    assert data["code"] == "PLAN-TEAM-GROWTH-MO"
    assert data["billing_interval"] == "monthly"
    assert data["base_price"] == 79.00
    assert data["setup_fee"] == 25.00
    assert data["min_quantity"] == 3
    assert data["trial_days"] == 14
    assert data["auto_renew"] is True
    assert len(data["features"]) == 4


def test_create_plan_all_billing_frequencies(client, admin_token):
    """Support all specified cadences: daily, weekly, monthly, quarterly, yearly."""
    frequencies = ["daily", "weekly", "monthly", "quarterly", "yearly"]
    for freq in frequencies:
        code = f"PLAN-TEST-{freq.upper()}"
        res = client.post(
            "/api/v1/plans",
            json={
                "name": f"Test {freq.capitalize()} Plan",
                "code": code,
                "billing_interval": freq,
                "base_price": 10.00,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 201, f"Failed for frequency: {freq}"
        assert res.json["data"]["billing_interval"] == freq


def test_create_plan_invalid_billing_frequency(client, admin_token):
    """Reject unpermitted billing frequencies with 422."""
    res = client.post(
        "/api/v1/plans",
        json={
            "name": "Invalid Cadence Plan",
            "code": "PLAN-INVALID-CADENCE",
            "billing_interval": "bi-weekly",
            "base_price": 50.00,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_BILLING_INTERVAL"


def test_create_plan_invalid_prices(client, admin_token):
    """Reject negative base_price and setup_fee with 422."""
    # Negative base price
    res_base = client.post(
        "/api/v1/plans",
        json={"name": "Bad Price", "code": "PLAN-NEG-BASE", "billing_interval": "monthly", "base_price": -20.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_base.status_code == 422
    assert res_base.json["error"]["code"] == "INVALID_PRICE"

    # Negative setup fee
    res_setup = client.post(
        "/api/v1/plans",
        json={"name": "Bad Setup", "code": "PLAN-NEG-SETUP", "billing_interval": "monthly", "base_price": 20.00, "setup_fee": -10.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_setup.status_code == 422
    assert res_setup.json["error"]["code"] == "INVALID_SETUP_FEE"


def test_create_plan_invalid_min_quantity(client, admin_token):
    """Minimum subscription quantity must be at least 1."""
    res = client.post(
        "/api/v1/plans",
        json={
            "name": "Bad Quantity",
            "code": "PLAN-BAD-QTY",
            "billing_interval": "monthly",
            "base_price": 50.00,
            "min_quantity": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_QUANTITY"


def test_create_plan_invalid_availability_dates(client, admin_token):
    """Reject inverted date ranges where available_until < available_from."""
    res = client.post(
        "/api/v1/plans",
        json={
            "name": "Inverted Dates",
            "code": "PLAN-INVERTED-DATES",
            "billing_interval": "monthly",
            "base_price": 50.00,
            "available_from": "2026-12-31",
            "available_until": "2026-01-01",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422
    assert res.json["error"]["code"] == "INVALID_DATE_RANGE"


def test_create_plan_duplicate_code(client, admin_token):
    """Duplicate plan code returns 409 Conflict."""
    payload = {"name": "First Plan", "code": "PLAN-DUPE-CODE", "billing_interval": "monthly", "base_price": 30.00}
    res1 = client.post("/api/v1/plans", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res1.status_code == 201

    res2 = client.post("/api/v1/plans", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
    assert res2.status_code == 409
    assert res2.json["error"]["code"] == "DUPLICATE_PLAN_CODE"


def test_customer_plan_availability_filtering(client, admin_token, customer_token):
    """Customer query filters out expired plans and inactive plans."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last_week = (date.today() - timedelta(days=7)).isoformat()

    # Expired plan
    client.post(
        "/api/v1/plans",
        json={
            "name": "Expired Promo Plan",
            "code": "PLAN-EXPIRED-PROMO",
            "billing_interval": "monthly",
            "base_price": 10.00,
            "available_from": last_week,
            "available_until": yesterday,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Active available plan
    client.post(
        "/api/v1/plans",
        json={
            "name": "Active Valid Plan",
            "code": "PLAN-ACTIVE-VALID",
            "billing_interval": "monthly",
            "base_price": 20.00,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Customer lists plans
    res = client.get("/api/v1/plans", headers={"Authorization": f"Bearer {customer_token}"})
    assert res.status_code == 200
    plan_codes = [p["code"] for p in res.json["data"]["items"]]
    assert "PLAN-ACTIVE-VALID" in plan_codes
    assert "PLAN-EXPIRED-PROMO" not in plan_codes


def test_update_plan_and_status_toggle(client, admin_token):
    """Test updating plan fields and toggling active status."""
    res_create = client.post(
        "/api/v1/plans",
        json={"name": "Old Plan Name", "code": "PLAN-UPDATE-ME", "billing_interval": "monthly", "base_price": 40.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    plan_id = res_create.json["data"]["id"]

    # Update plan
    res_update = client.put(
        f"/api/v1/plans/{plan_id}",
        json={
            "name": "New Plan Name",
            "base_price": 45.00,
            "billing_interval": "yearly",
            "min_quantity": 5,
            "features": ["Feature A", "Feature B"],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_update.status_code == 200
    data = res_update.json["data"]
    assert data["name"] == "New Plan Name"
    assert data["base_price"] == 45.00
    assert data["billing_interval"] == "yearly"
    assert data["min_quantity"] == 5
    assert len(data["features"]) == 2

    # Toggle status to inactive
    res_stat = client.patch(
        f"/api/v1/plans/{plan_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_stat.status_code == 200
    assert res_stat.json["data"]["is_active"] is False


def test_delete_plan(client, admin_token):
    """Admin can delete a plan that is not linked to any subscriptions or quotations."""
    res_create = client.post(
        "/api/v1/plans",
        json={"name": "Temp Plan", "code": "PLAN-TO-DELETE", "billing_interval": "monthly", "base_price": 15.00},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    plan_id = res_create.json["data"]["id"]

    res_del = client.delete(f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_del.status_code == 200

    # Verify 404 after deletion
    res_get = client.get(f"/api/v1/plans/{plan_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_get.status_code == 404

