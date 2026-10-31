from flask import Blueprint, request
from backend.models.invoice import Invoice
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


@invoices_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_invoices():
    """
    List invoices with filtering by status, customer, or subscription.
    """
    page, per_page = get_pagination_params()
    query = Invoice.query

    status = request.args.get("status")
    if status:
        query = query.filter_by(status=status)

    customer_id = request.args.get("customer_id", type=int)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)

    subscription_id = request.args.get("subscription_id", type=int)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    query = query.order_by(Invoice.invoice_date.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Invoices retrieved")


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_invoice(invoice_id: int):
    """Retrieve detailed invoice view with line items and allocations."""
    invoice = Invoice.query.get_or_404(invoice_id)
    return api_response(data=invoice.to_dict(), message="Invoice retrieved")
