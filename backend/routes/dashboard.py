from datetime import date
from flask import Blueprint, g
from sqlalchemy import func, or_, and_
from backend.extensions import db
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from backend.models.payment import Payment
from backend.utils.response import api_response
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _get_customer_id_for_current_user() -> int | None:
    if not hasattr(g, "current_user") or not g.current_user:
        return None
    if g.current_user.role == ROLE_CUSTOMER:
        return g.current_user.customer_profile.id if g.current_user.customer_profile else -1
    return None


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
    Strictly isolated for customers.
    """
    today = date.today()
    cust_id = _get_customer_id_for_current_user()

    # 1. Active Subscriptions
    sub_q = Subscription.query
    if cust_id is not None:
        sub_q = sub_q.filter_by(customer_id=cust_id)
    active_subscriptions_count = sub_q.filter_by(status="active").count()
    total_subscriptions_count = sub_q.count()

    # 2. Total Revenue (sum of completed payments)
    rev_q = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.status == "completed"
    )
    if cust_id is not None:
        rev_q = rev_q.filter(Payment.customer_id == cust_id)
    revenue_sum = rev_q.scalar()

    # 3. Outstanding Invoices (posted or partial with remaining balance)
    outstanding_invoices_query = Invoice.query.filter(
        Invoice.status.in_(["posted", "partial"]),
        Invoice.balance_due > 0
    )
    if cust_id is not None:
        outstanding_invoices_query = outstanding_invoices_query.filter(Invoice.customer_id == cust_id)
    outstanding_invoices_count = outstanding_invoices_query.count()

    out_amt_q = db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(
        Invoice.status.in_(["posted", "partial"]),
        Invoice.balance_due > 0
    )
    if cust_id is not None:
        out_amt_q = out_amt_q.filter(Invoice.customer_id == cust_id)
    outstanding_invoices_amount = out_amt_q.scalar()

    # 4. Overdue Invoices
    overdue_cond = or_(
        Invoice.status == "overdue",
        and_(
            Invoice.status.in_(["posted", "partial"]),
            Invoice.due_date < today,
            Invoice.balance_due > 0
        )
    )
    overdue_invoices_query = Invoice.query.filter(overdue_cond)
    if cust_id is not None:
        overdue_invoices_query = overdue_invoices_query.filter(Invoice.customer_id == cust_id)
    overdue_invoices_count = overdue_invoices_query.count()

    overdue_amt_q = db.session.query(
        func.coalesce(func.sum(Invoice.balance_due), 0)
    ).filter(overdue_cond)
    if cust_id is not None:
        overdue_amt_q = overdue_amt_q.filter(Invoice.customer_id == cust_id)
    overdue_invoices_amount = overdue_amt_q.scalar()

    # Recent items
    rec_inv_q = Invoice.query
    rec_sub_q = Subscription.query
    if cust_id is not None:
        rec_inv_q = rec_inv_q.filter_by(customer_id=cust_id)
        rec_sub_q = rec_sub_q.filter_by(customer_id=cust_id)

    recent_invoices = rec_inv_q.order_by(Invoice.created_at.desc()).limit(5).all()
    recent_subscriptions = rec_sub_q.order_by(Subscription.created_at.desc()).limit(5).all()

    # Determine whether the user/workspace has zero operational records
    total_inv_count = rec_inv_q.count()
    total_pay_q = Payment.query
    if cust_id is not None:
        total_pay_q = total_pay_q.filter_by(customer_id=cust_id)
    total_payments_count = total_pay_q.count()

    is_empty = (total_subscriptions_count == 0 and total_inv_count == 0 and total_payments_count == 0)

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
