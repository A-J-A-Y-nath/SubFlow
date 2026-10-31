from flask import Blueprint, request
from backend.models.quotation import Quotation
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

quotations_bp = Blueprint("quotations", __name__, url_prefix="/quotations")


@quotations_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_quotations():
    """
    List quotations with status and customer filtering.
    """
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
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_quotation(quotation_id: int):
    """Retrieve detailed quotation with line items."""
    quotation = Quotation.query.get_or_404(quotation_id)
    return api_response(data=quotation.to_dict(), message="Quotation retrieved")
