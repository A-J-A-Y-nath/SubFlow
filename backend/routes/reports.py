from datetime import datetime, timezone, timedelta
from flask import Blueprint
from sqlalchemy import func
from backend.extensions import db
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from backend.models.plan import Plan
from backend.utils.response import api_response
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/analytics", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def get_analytics():
    """
    Generate aggregated data formatted for dashboard and reporting charts (Recharts).
    """
    # 1. Subscriptions by Plan
    plan_distribution = db.session.query(
        Plan.name,
        func.count(Subscription.id).label("count")
    ).outerjoin(Subscription, Subscription.plan_id == Plan.id)\
     .group_by(Plan.name).all()

    # 2. Invoices by Status
    invoice_status_breakdown = db.session.query(
        Invoice.status,
        func.count(Invoice.id).label("count"),
        func.coalesce(func.sum(Invoice.total_amount), 0).label("total_amount")
    ).group_by(Invoice.status).all()

    # 3. Monthly recurring revenue estimate
    mrr_estimate = db.session.query(
        func.coalesce(func.sum(Subscription.recurring_amount), 0)
    ).filter(Subscription.status == "active").scalar()

    payload = {
        "mrr_estimate": float(mrr_estimate),
        "plan_distribution": [
            {"plan": row[0], "subscriptions": row[1]} for row in plan_distribution
        ],
        "invoice_status_breakdown": [
            {"status": row[0], "count": row[1], "total_amount": float(row[2])} for row in invoice_status_breakdown
        ],
    }

    return api_response(data=payload, message="Analytics data retrieved")
