from flask import Blueprint, request
from backend.models.subscription import Subscription
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

subscriptions_bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@subscriptions_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_subscriptions():
    """
    List subscriptions with status and customer filtering.
    """
    page, per_page = get_pagination_params()
    query = Subscription.query

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    query = query.order_by(Subscription.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Subscriptions retrieved")


@subscriptions_bp.route("/<int:subscription_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_subscription(subscription_id: int):
    """Retrieve detailed view of a subscription including line items."""
    subscription = Subscription.query.get_or_404(subscription_id)
    return api_response(data=subscription.to_dict(), message="Subscription retrieved")
