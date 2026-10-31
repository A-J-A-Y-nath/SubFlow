from flask import Blueprint, request
from backend.models.payment import Payment
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


@payments_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_payments():
    """
    List payments with method, status, and customer filtering.
    """
    page, per_page = get_pagination_params()
    query = Payment.query

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    payment_method = request.args.get("payment_method")
    if payment_method:
        query = query.filter_by(payment_method=payment_method)

    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    query = query.order_by(Payment.payment_date.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Payments retrieved")


@payments_bp.route("/<int:payment_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_payment(payment_id: int):
    """Retrieve detailed payment transaction with allocations."""
    payment = Payment.query.get_or_404(payment_id)
    return api_response(data=payment.to_dict(), message="Payment retrieved")
