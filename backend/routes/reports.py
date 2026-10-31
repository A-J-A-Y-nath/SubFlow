from flask import Blueprint, request, g
from sqlalchemy import func
from backend.extensions import db
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from backend.models.plan import Plan
from backend.services.analytics_service import AnalyticsService
from backend.utils.response import api_response
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _get_customer_id_for_current_user() -> int | None:
    if not hasattr(g, "current_user") or not g.current_user:
        return None
    if g.current_user.role == ROLE_CUSTOMER:
        return g.current_user.customer_profile.id if g.current_user.customer_profile else -1
    return None


@reports_bp.route("/analytics", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_analytics():
    """
    Comprehensive aggregated financial analytics endpoint formatted for Recharts.
    Query parameters:
    - range: '7d', '30d', 'month', 'year', 'all' (default: '30d')
    """
    range_filter = request.args.get("range", "30d").lower()
    start_date, end_date = AnalyticsService.parse_date_range(range_filter)

    customer_id = _get_customer_id_for_current_user()

    # 1. High-level financial KPIs
    financial_summary = AnalyticsService.get_financial_summary(
        start_date=start_date,
        end_date=end_date,
        customer_id=customer_id
    )

    # 2. Revenue timeline trends for line/area chart
    trend_period = "daily" if range_filter in ("7d", "30d", "month") else "monthly"
    revenue_trends = AnalyticsService.get_revenue_trends(
        period=trend_period,
        start_date=start_date,
        end_date=end_date,
        customer_id=customer_id
    )

    # 3. Subscriptions by Plan (Bar Chart)
    plan_query = db.session.query(
        Plan.name,
        func.count(Subscription.id).label("count")
    ).outerjoin(
        Subscription,
        (Subscription.plan_id == Plan.id) & (Subscription.status == "active")
    )
    if customer_id:
        plan_query = plan_query.filter(Subscription.customer_id == customer_id)
    plan_distribution = plan_query.group_by(Plan.name).all()

    # 4. Invoices by Status (Pie / Donut Chart)
    invoice_status_breakdown = AnalyticsService.get_invoice_status_breakdown(customer_id=customer_id)

    # 5. Payment Methods Distribution
    payment_methods = AnalyticsService.get_payment_method_breakdown(customer_id=customer_id)

    # 6. Accounts Receivable Aging Report
    aging_report = AnalyticsService.get_aging_report(customer_id=customer_id)

    # 7. Monthly Recurring Revenue (MRR) estimate
    mrr_query = db.session.query(
        func.coalesce(func.sum(Subscription.recurring_amount), 0)
    ).filter(Subscription.status == "active")
    if customer_id:
        mrr_query = mrr_query.filter(Subscription.customer_id == customer_id)
    mrr_estimate = float(mrr_query.scalar() or 0.0)

    payload = {
        "range": range_filter,
        "mrr_estimate": mrr_estimate,
        "financial_summary": financial_summary,
        "revenue_trends": revenue_trends,
        "plan_distribution": [
            {"plan": row[0], "subscriptions": row[1]} for row in plan_distribution
        ],
        "invoice_status_breakdown": invoice_status_breakdown,
        "payment_methods": payment_methods,
        "aging_report": aging_report,
    }

    return api_response(data=payload, message="Analytics data retrieved successfully")


@reports_bp.route("/revenue", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_revenue_report():
    """Returns standalone revenue trend series."""
    range_filter = request.args.get("range", "30d").lower()
    period = request.args.get("period", "daily").lower()
    start_date, end_date = AnalyticsService.parse_date_range(range_filter)
    customer_id = _get_customer_id_for_current_user()

    trends = AnalyticsService.get_revenue_trends(
        period=period,
        start_date=start_date,
        end_date=end_date,
        customer_id=customer_id
    )
    return api_response(data=trends, message="Revenue report retrieved")


@reports_bp.route("/aging", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_aging_report():
    """Returns receivables aging analysis."""
    customer_id = _get_customer_id_for_current_user()
    aging = AnalyticsService.get_aging_report(customer_id=customer_id)
    return api_response(data=aging, message="Aging report retrieved")
