"""
Subscriptions Routes — SubFlow Member 3
Full CRUD with state-machine transitions, customer scoping, and renewal.
"""
from flask import Blueprint, request, g
from backend.extensions import db
from backend.models.subscription import Subscription
from backend.models.customer import Customer
from backend.services.subscription_service import (
    create_subscription,
    update_subscription_status,
    renew_subscription,
)
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


def _customer_id_for_user(user) -> int | None:
    """Return the customer.id linked to a customer-role user, or None."""
    if user.role == ROLE_CUSTOMER:
        linked = Customer.query.filter_by(user_id=user.id).first()
        return linked.id if linked else None
    return None


@subscriptions_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_subscriptions():
    """List subscriptions — customers see only their own."""
    page, per_page = get_pagination_params()
    query = Subscription.query

    # Customers are scoped to their own records
    user = g.current_user
    if user.role == ROLE_CUSTOMER:
        cid = _customer_id_for_user(user)
        if cid is None:
            return api_response(data={"items": [], "pagination": {}}, message="No customer profile linked")
        query = query.filter_by(customer_id=cid)
    else:
        customer_id = request.args.get("customer_id", type=int)
        if customer_id:
            query = query.filter_by(customer_id=customer_id)

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    query = query.order_by(Subscription.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Subscriptions retrieved")


@subscriptions_bp.route("/<int:subscription_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_subscription(subscription_id: int):
    """Retrieve a subscription — customers may only view their own."""
    sub = Subscription.query.get_or_404(subscription_id)

    user = g.current_user
    if user.role == ROLE_CUSTOMER:
        cid = _customer_id_for_user(user)
        if sub.customer_id != cid:
            return api_error("FORBIDDEN", "Access denied to this subscription", status_code=403)

    return api_response(data=sub.to_dict(), message="Subscription retrieved")


@subscriptions_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_subscription_route():
    """Create a new subscription (admin/staff only)."""
    data = request.get_json(silent=True) or {}
    subscription, err = create_subscription(data, g.current_user)
    if err:
        return err
    return api_response(data=subscription.to_dict(), message="Subscription created", status_code=201)


@subscriptions_bp.route("/<int:subscription_id>/status", methods=["PATCH"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def change_subscription_status(subscription_id: int):
    """Change subscription status (admin/staff only — enforces state machine)."""
    sub = Subscription.query.get_or_404(subscription_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return api_error("MISSING_FIELD", "status is required", status_code=422)

    sub, err = update_subscription_status(sub, new_status, g.current_user, reason=data.get("reason"))
    if err:
        return err
    return api_response(data=sub.to_dict(), message=f"Subscription status updated to '{new_status}'")


@subscriptions_bp.route("/<int:subscription_id>/renew", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def renew_subscription_route(subscription_id: int):
    """Renew a subscription — advances billing period (admin/staff only)."""
    sub = Subscription.query.get_or_404(subscription_id)
    sub, err = renew_subscription(sub, g.current_user)
    if err:
        return err
    return api_response(data=sub.to_dict(), message="Subscription renewed successfully")
