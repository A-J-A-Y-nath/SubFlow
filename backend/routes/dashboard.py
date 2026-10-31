from datetime import date
from flask import Blueprint
from sqlalchemy import func, or_, and_
from backend.extensions import db
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from backend.models.payment import Payment
from backend.utils.response import api_response
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/summary", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_dashboard_summary():
    """
    Returns dashboard summary statistics:
    - Active subscriptions count
    - Total revenue (sum of completed payments)
    - Outstanding invoices (count and total balance due)
    - Overdue invoices (count and total balance due)
    - Activity and empty state indicator
    """
    today = date.today()

    # 1. Active Subscriptions
    active_subscriptions_count = Subscription.query.filter_by(status="active").count()
    total_subscriptions_count = Subscription.query.count()

    # 2. Total Revenue (sum of completed payments)
    revenue_sum = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed"
    ).scalar()

    # 3. Outstanding Invoices (posted or partial with remaining balance)
    outstanding_invoices_query = Invoice.query.filter(
        Invoice.status.in_(["posted", "partial"]),
        Invoice.balance_due > 0
    )
    outstanding_invoices_count = outstanding_invoices_query.count()
    outstanding_invoices_amount = db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(
        Invoice.status.in_(["posted", "partial"]),
        Invoice.balance_due > 0
    ).scalar()

    # 4. Overdue Invoices
    overdue_invoices_query = Invoice.query.filter(
        or_(
            Invoice.status == "overdue",
            and_(
                Invoice.status.in_(["posted", "partial"]),
                Invoice.due_date < today,
                Invoice.balance_due > 0
            )
        )
    )
    overdue_invoices_count = overdue_invoices_query.count()
    overdue_invoices_amount = db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(
        or_(
            Invoice.status == "overdue",
            and_(
                Invoice.status.in_(["posted", "partial"]),
                Invoice.due_date < today,
                Invoice.balance_due > 0
            )
        )
    ).scalar()

    # Recent items
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    recent_subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).limit(5).all()

    # Determine whether the entire workspace has zero operational records
    total_invoices_count = Invoice.query.count()
    total_payments_count = Payment.query.count()
    is_empty = (total_subscriptions_count == 0 and total_invoices_count == 0 and total_payments_count == 0)

    payload = {
        "is_empty": is_empty,
        "metrics": {
            "active_subscriptions": {
                "count": active_subscriptions_count,
                "total": total_subscriptions_count,
                "label": "Active Subscriptions"
            },
            "total_revenue": {
                "amount": float(revenue_sum),
                "currency": "USD",
                "label": "Total Revenue"
            },
            "outstanding_invoices": {
                "count": outstanding_invoices_count,
                "amount": float(outstanding_invoices_amount),
                "currency": "USD",
                "label": "Outstanding Invoices"
            },
            "overdue_invoices": {
                "count": overdue_invoices_count,
                "amount": float(overdue_invoices_amount),
                "currency": "USD",
                "label": "Overdue Invoices"
            }
        },
        "recent_invoices": [inv.to_dict() for inv in recent_invoices],
        "recent_subscriptions": [sub.to_dict() for sub in recent_subscriptions],
    }

    return api_response(data=payload, message="Dashboard summary loaded successfully")
