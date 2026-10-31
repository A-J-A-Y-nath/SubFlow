from flask import Blueprint, request
from backend.models.discount import DiscountRule
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

discounts_bp = Blueprint("discounts", __name__, url_prefix="/discounts")


@discounts_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_discounts():
    """
    List discount rules and promotional coupons.
    """
    page, per_page = get_pagination_params()
    query = DiscountRule.query

    active_only = request.args.get("is_active")
    if active_only is not None:
        query = query.filter_by(is_active=(active_only.lower() in ("true", "1")))

    query = query.order_by(DiscountRule.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Discount rules retrieved")


@discounts_bp.route("/validate/<code>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def validate_coupon_code(code: str):
    """
    Check if a specific coupon code is active and valid.
    """
    coupon = DiscountRule.query.filter_by(code=code.strip().upper()).first()
    if not coupon:
        return api_error(code="COUPON_NOT_FOUND", message="Invalid coupon code", status_code=404)

    if not coupon.is_valid_now():
        return api_error(code="COUPON_EXPIRED", message="This coupon is no longer valid", status_code=400)

    return api_response(data=coupon.to_dict(), message="Coupon is valid")
