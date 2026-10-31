from flask import Blueprint, request
from backend.models.plan import Plan
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

plans_bp = Blueprint("plans", __name__, url_prefix="/plans")


@plans_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_plans():
    """
    List subscription plans with interval filter (e.g., monthly, yearly).
    """
    page, per_page = get_pagination_params(default_per_page=50)
    query = Plan.query

    interval = request.args.get("billing_interval")
    if interval:
        query = query.filter_by(billing_interval=interval)

    active_only = request.args.get("is_active")
    if active_only is not None:
        query = query.filter_by(is_active=(active_only.lower() in ("true", "1")))

    query = query.order_by(Plan.base_price.asc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Subscription plans retrieved")


@plans_bp.route("/<int:plan_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_plan(plan_id: int):
    """Retrieve details for a specific plan."""
    plan = Plan.query.get_or_404(plan_id)
    return api_response(data=plan.to_dict(), message="Plan details retrieved")
