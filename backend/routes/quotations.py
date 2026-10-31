"""
Quotations Routes — SubFlow Member 3
Full CRUD: list, create, detail, update, send, confirm→subscription.
"""
from flask import Blueprint, request, g
from backend.models.quotation import Quotation
from backend.services.quotation_service import (
    create_quotation,
    update_quotation,
    send_quotation,
    confirm_quotation,
    expire_stale_quotations,
)
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

quotations_bp = Blueprint("quotations", __name__, url_prefix="/quotations")


@quotations_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def list_quotations():
    """List quotations with status and customer filtering (admin/staff only)."""
    page, per_page = get_pagination_params()
    query = Quotation.query

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    query = query.order_by(Quotation.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Quotations retrieved")


@quotations_bp.route("/<int:quotation_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def get_quotation(quotation_id: int):
    """Retrieve detailed quotation with line items."""
    quotation = Quotation.query.get_or_404(quotation_id)
    return api_response(data=quotation.to_dict(), message="Quotation retrieved")


@quotations_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_quotation_route():
    """Create a new quotation (admin/staff only)."""
    data = request.get_json(silent=True) or {}
    quotation, err = create_quotation(data, g.current_user)
    if err:
        return err
    return api_response(data=quotation.to_dict(), message="Quotation created", status_code=201)


@quotations_bp.route("/<int:quotation_id>", methods=["PATCH"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def update_quotation_route(quotation_id: int):
    """Update a draft or sent quotation (admin/staff only)."""
    quotation = Quotation.query.get_or_404(quotation_id)
    data = request.get_json(silent=True) or {}
    quotation, err = update_quotation(quotation, data, g.current_user)
    if err:
        return err
    return api_response(data=quotation.to_dict(), message="Quotation updated")


@quotations_bp.route("/<int:quotation_id>/send", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def send_quotation_route(quotation_id: int):
    """Mark a draft quotation as sent (admin/staff only)."""
    quotation = Quotation.query.get_or_404(quotation_id)
    quotation, err = send_quotation(quotation, g.current_user)
    if err:
        return err
    return api_response(data=quotation.to_dict(), message="Quotation sent to customer")


@quotations_bp.route("/<int:quotation_id>/confirm", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def confirm_quotation_route(quotation_id: int):
    """
    Confirm (approve) a quotation — creates a linked Subscription.
    Body: { start_date: 'YYYY-MM-DD' (optional), auto_renew: bool (optional) }
    """
    quotation = Quotation.query.get_or_404(quotation_id)
    data = request.get_json(silent=True) or {}
    quotation, subscription, err = confirm_quotation(quotation, data, g.current_user)
    if err:
        return err
    return api_response(
        data={
            "quotation": quotation.to_dict(),
            "subscription": subscription.to_dict(),
        },
        message="Quotation confirmed and subscription created",
        status_code=201,
    )


@quotations_bp.route("/expire-stale", methods=["POST"])
@role_required(ROLE_ADMIN)
def expire_stale_route():
    """Admin utility: expire all overdue draft/sent quotations."""
    count = expire_stale_quotations()
    return api_response(data={"expired_count": count}, message=f"{count} quotations expired")
