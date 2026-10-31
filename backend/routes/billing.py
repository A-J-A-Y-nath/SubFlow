"""
Billing Routes — SubFlow Member 3
Admin-only endpoints to trigger and preview the recurring billing cycle.
"""
from datetime import date
from flask import Blueprint, request, g
from backend.services.billing_service import run_billing_cycle, get_subscriptions_due_for_billing
from backend.utils.response import api_response, api_error
from backend.utils.decorators import role_required, ROLE_ADMIN

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/run", methods=["POST"])
@role_required(ROLE_ADMIN)
def run_billing():
    """
    Trigger the recurring billing cycle (admin only).
    Body: { as_of_date: 'YYYY-MM-DD' } — defaults to today.
    """
    data = request.get_json(silent=True) or {}
    as_of_str = data.get("as_of_date")

    as_of_date = None
    if as_of_str:
        try:
            as_of_date = date.fromisoformat(as_of_str)
        except ValueError:
            return api_error("INVALID_DATE", "as_of_date must be ISO 8601 format (YYYY-MM-DD)", status_code=422)

    result = run_billing_cycle(as_of_date)
    return api_response(data=result, message="Billing cycle completed")


@billing_bp.route("/due", methods=["GET"])
@role_required(ROLE_ADMIN)
def preview_due():
    """
    Preview which subscriptions are due for billing today (admin only).
    Query param: as_of_date=YYYY-MM-DD (optional, defaults to today).
    """
    as_of_str = request.args.get("as_of_date")
    as_of_date = None
    if as_of_str:
        try:
            as_of_date = date.fromisoformat(as_of_str)
        except ValueError:
            return api_error("INVALID_DATE", "as_of_date must be ISO 8601 format (YYYY-MM-DD)", status_code=422)

    due = get_subscriptions_due_for_billing(as_of_date)
    return api_response(
        data={
            "as_of_date": (as_of_date or date.today()).isoformat(),
            "due_count": len(due),
            "subscriptions": [s.to_dict() for s in due],
        },
        message=f"{len(due)} subscription(s) due for billing"
    )
