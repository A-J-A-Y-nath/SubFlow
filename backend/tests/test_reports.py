import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from backend.models import Customer, Invoice, Payment
from backend.services.billing_service import BillingService
from backend.services.payment_service import PaymentService
from backend.services.analytics_service import AnalyticsService
from backend.extensions import db


def test_analytics_revenue_calculation_only_completed(customer_user):
    """Test that revenue calculation counts only completed payments and excludes failed/pending."""
    # Completed payment $150
    PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("150.00"),
        status="completed"
    )
    # Pending payment $200 (should not be in revenue)
    PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("200.00"),
        status="pending"
    )
    # Failed payment $300 (should not be in revenue)
    PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("300.00"),
        status="failed"
    )
    db.session.commit()

    summary = AnalyticsService.get_financial_summary()
    assert summary["total_revenue"] == 150.00
    assert summary["completed_payments_count"] == 1


def test_receivables_aging_breakdown(customer_user):
    """Test receivables aging grouping by due dates."""
    today = date.today()
    # 1. Current (due in future)
    BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=today,
        due_date=today + date.resolution * 15,
        lines=[{"description": "Current item", "quantity": 1, "unit_price": 100.00}],
        status="posted"
    )
    # 2. 1-30 days overdue
    BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=today - date.resolution * 40,
        due_date=today - date.resolution * 10,
        lines=[{"description": "10d overdue item", "quantity": 1, "unit_price": 50.00}],
        status="posted"
    )
    # 3. 31-60 days overdue
    BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=today - date.resolution * 70,
        due_date=today - date.resolution * 40,
        lines=[{"description": "40d overdue item", "quantity": 1, "unit_price": 75.00}],
        status="posted"
    )
    db.session.commit()

    aging = AnalyticsService.get_aging_report()
    assert aging["current"]["amount"] == 100.00
    assert aging["current"]["count"] == 1
    assert aging["1_30"]["amount"] == 50.00
    assert aging["1_30"]["count"] == 1
    assert aging["31_60"]["amount"] == 75.00
    assert aging["31_60"]["count"] == 1


def test_reports_api_endpoint(client, admin_token):
    """Test GET /api/v1/reports/analytics endpoint format for Recharts."""
    res = client.get(
        "/api/v1/reports/analytics?range=30d",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    assert res.json["success"] is True
    data = res.json["data"]
    assert "financial_summary" in data
    assert "revenue_trends" in data
    assert "plan_distribution" in data
    assert "invoice_status_breakdown" in data
    assert "aging_report" in data
    assert "payment_methods" in data
