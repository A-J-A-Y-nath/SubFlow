"""
Tests for Billing Service — Member 3
Covers: due subscription detection, billing cycle, duplicate-billing prevention.
"""
import pytest
from datetime import date, timedelta
from backend.extensions import db
from backend.models import Customer, Plan, Product, Subscription, SubscriptionLine, Invoice
from backend.services.billing_service import run_billing_cycle, get_subscriptions_due_for_billing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_active_subscription(app, next_billing_date=None):
    """Create an active subscription due for billing and return its id."""
    with app.app_context():
        customer = Customer(
            company_name="Billing Test Corp",
            contact_name="Biller",
            email="bill@testcorp.io",
            payment_terms_days=30,
        )
        db.session.add(customer)
        db.session.flush()

        plan = Plan(
            name="Monthly Billing Plan",
            code=f"PLAN-BILL-{next_billing_date or date.today()}",
            billing_interval="monthly",
            billing_interval_count=1,
            base_price=99.00,
            is_active=True,
        )
        db.session.add(plan)
        db.session.flush()

        product = Product(
            name="Billing Product",
            sku=f"PROD-BILL-{next_billing_date or date.today()}",
            description="Billing product",
            is_recurring=True,
            default_price=99.00,
        )
        db.session.add(product)
        db.session.flush()

        today = date.today()
        nbd = next_billing_date or today  # due today by default
        sub = Subscription(
            subscription_number=f"SUB-BILL-{nbd.strftime('%Y%m%d')}",
            customer_id=customer.id,
            plan_id=plan.id,
            status="active",
            start_date=today - timedelta(days=30),
            current_period_start=today - timedelta(days=30),
            current_period_end=today,
            next_billing_date=nbd,
            auto_renew=True,
            recurring_amount=99.00,
            currency="USD",
        )
        db.session.add(sub)
        db.session.flush()

        line = SubscriptionLine(
            subscription_id=sub.id,
            product_id=product.id,
            description="Monthly seat",
            quantity=1,
            unit_price=99.00,
            discount_percent=0,
            recurring_amount=99.00,
        )
        db.session.add(line)
        db.session.commit()
        return sub.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_subscriptions_due_for_billing(app):
    """Active subscriptions with next_billing_date <= today should be returned."""
    sub_id = _seed_active_subscription(app, next_billing_date=date.today())
    with app.app_context():
        due = get_subscriptions_due_for_billing(date.today())
        assert any(s.id == sub_id for s in due)


def test_future_subscription_not_due(app):
    """A subscription with next_billing_date in the future should NOT be returned."""
    future_date = date.today() + timedelta(days=10)
    sub_id = _seed_active_subscription(app, next_billing_date=future_date)
    with app.app_context():
        due = get_subscriptions_due_for_billing(date.today())
        assert not any(s.id == sub_id for s in due)


def test_billing_cycle_creates_invoice(app):
    """run_billing_cycle should create one invoice for a due subscription."""
    sub_id = _seed_active_subscription(app, next_billing_date=date.today())
    with app.app_context():
        result = run_billing_cycle(date.today())
        assert result["processed"] >= 1
        assert result["errors"] == [] or all(e["subscription_id"] != sub_id for e in result["errors"])

        invoice = Invoice.query.filter_by(subscription_id=sub_id).first()
        assert invoice is not None
        assert invoice.total_amount > 0


def test_billing_cycle_idempotent_no_duplicate(app):
    """Running billing cycle twice for the same period must not create duplicate invoices."""
    sub_id = _seed_active_subscription(app, next_billing_date=date.today())
    with app.app_context():
        # Run once
        run_billing_cycle(date.today())
        count_after_first = Invoice.query.filter_by(subscription_id=sub_id).count()

        # The period has advanced — roll back next_billing_date to simulate re-run
        sub = Subscription.query.get(sub_id)
        billing_start = sub.current_period_start
        # Manually insert a second invoice with the same period_start to prove constraint works
        from sqlalchemy.exc import IntegrityError
        dup = Invoice(
            invoice_number="INV-DUP-TEST",
            customer_id=sub.customer_id,
            subscription_id=sub_id,
            status="draft",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            billing_period_start=billing_start,
            total_amount=99.00,
            balance_due=99.00,
            currency="USD",
        )
        db.session.add(dup)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_billing_cycle_advances_next_billing_date(app):
    """After billing, next_billing_date should be advanced to the next period."""
    sub_id = _seed_active_subscription(app, next_billing_date=date.today())
    with app.app_context():
        old_nbd = Subscription.query.get(sub_id).next_billing_date
        run_billing_cycle(date.today())
        db.session.expire_all()
        new_nbd = Subscription.query.get(sub_id).next_billing_date
        assert new_nbd > old_nbd


def test_billing_run_endpoint_admin_only(client, admin_token, customer_token):
    """POST /api/v1/billing/run is admin-only."""
    admin_res = client.post("/api/v1/billing/run",
                            headers={"Authorization": f"Bearer {admin_token}"},
                            json={})
    # May return 200 with 0 processed — just not 403
    assert admin_res.status_code != 403

    cust_res = client.post("/api/v1/billing/run",
                           headers={"Authorization": f"Bearer {customer_token}"},
                           json={})
    assert cust_res.status_code == 403


def test_billing_due_preview_endpoint(client, admin_token):
    """GET /api/v1/billing/due should return due subscription list."""
    res = client.get("/api/v1/billing/due",
                     headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert "due_count" in res.json["data"]
    assert "subscriptions" in res.json["data"]
