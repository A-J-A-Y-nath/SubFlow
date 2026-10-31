import pytest
from datetime import date, timedelta
from decimal import Decimal
from backend.models import Plan, Subscription, SubscriptionLine, Invoice
from backend.services.billing_service import BillingService, advance_date_by_interval
from backend.extensions import db


@pytest.fixture
def test_plan_monthly():
    plan = Plan(
        name="Pro Monthly",
        code="PLAN-TEST-MO",
        billing_interval="monthly",
        billing_interval_count=1,
        base_price=99.00,
        trial_days=0,
        is_active=True
    )
    db.session.add(plan)
    db.session.commit()
    return plan


@pytest.fixture
def active_subscription(customer_user, test_plan_monthly):
    today = date.today()
    period_start = today - timedelta(days=30)
    period_end = today
    sub = Subscription(
        subscription_number="SUB-TEST-0001",
        customer_id=customer_user.customer_id,
        plan_id=test_plan_monthly.id,
        status="active",
        start_date=period_start,
        current_period_start=period_start,
        current_period_end=period_end,
        next_billing_date=today,
        auto_renew=True,
        recurring_amount=Decimal("99.00"),
        currency="USD"
    )
    db.session.add(sub)
    db.session.commit()
    return sub


def test_advance_date_intervals():
    """Test date advancement for daily, weekly, monthly, quarterly, and yearly cadences."""
    start = date(2026, 1, 31)
    # Monthly: Jan 31 -> Feb 28
    assert advance_date_by_interval(start, "monthly", 1) == date(2026, 2, 28)
    # Daily
    assert advance_date_by_interval(start, "daily", 5) == date(2026, 2, 5)
    # Weekly
    assert advance_date_by_interval(start, "weekly", 2) == date(2026, 2, 14)
    # Quarterly
    assert advance_date_by_interval(start, "quarterly", 1) == date(2026, 4, 30)
    # Yearly
    assert advance_date_by_interval(start, "yearly", 1) == date(2027, 1, 31)


def test_recurring_billing_generates_invoice(active_subscription):
    """Test that due active subscription generates a posted invoice and advances next_billing_date."""
    results = BillingService.generate_recurring_invoices(target_date=date.today())
    assert results["total_due_subscriptions"] >= 1
    assert len(results["generated_invoices"]) >= 1

    gen = results["generated_invoices"][0]
    assert gen["subscription_id"] == active_subscription.id
    assert gen["total_amount"] == 99.00

    # Verify subscription was advanced
    sub = db.session.get(Subscription, active_subscription.id)
    assert sub.next_billing_date > date.today()

    # Verify invoice was posted
    inv = Invoice.query.filter_by(subscription_id=active_subscription.id).first()
    assert inv is not None
    assert inv.status == "posted"
    assert float(inv.total_amount) == 99.00


def test_recurring_billing_idempotency_duplicate_prevention(active_subscription):
    """Test that running recurring billing twice on same date does not produce duplicate invoices."""
    res1 = BillingService.generate_recurring_invoices(target_date=date.today())
    assert len(res1["generated_invoices"]) >= 1

    # Second run immediately
    res2 = BillingService.generate_recurring_invoices(target_date=date.today())
    # Should find 0 due because next_billing_date was advanced
    assert len(res2["generated_invoices"]) == 0

    total_invoices = Invoice.query.filter_by(subscription_id=active_subscription.id).count()
    assert total_invoices == 1


def test_recurring_billing_skips_paused_and_trial(customer_user, test_plan_monthly):
    """Test that paused subscriptions or subscriptions in trial are excluded from billing."""
    today = date.today()
    paused_sub = Subscription(
        subscription_number="SUB-PAUSED",
        customer_id=customer_user.customer_id,
        plan_id=test_plan_monthly.id,
        status="paused",
        start_date=today - timedelta(days=30),
        current_period_start=today - timedelta(days=30),
        current_period_end=today,
        next_billing_date=today,
        auto_renew=True
    )

    trial_sub = Subscription(
        subscription_number="SUB-TRIAL",
        customer_id=customer_user.customer_id,
        plan_id=test_plan_monthly.id,
        status="active",
        start_date=today - timedelta(days=5),
        current_period_start=today - timedelta(days=5),
        current_period_end=today + timedelta(days=25),
        trial_end=today + timedelta(days=10),
        next_billing_date=today,
        auto_renew=True
    )
    db.session.add_all([paused_sub, trial_sub])
    db.session.commit()

    results = BillingService.generate_recurring_invoices(target_date=today)
    gen_ids = [g["subscription_id"] for g in results["generated_invoices"]]
    assert paused_sub.id not in gen_ids
    assert trial_sub.id not in gen_ids
