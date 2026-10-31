"""
Invoices Routes — SubFlow Member 3
Full lifecycle: list, create (manual), detail, confirm, cancel.
Customers see only their own invoices.
"""
from flask import Blueprint, request, g
from backend.models.invoice import Invoice
from backend.models.customer import Customer
from backend.services.invoice_service import (
    create_invoice_manual,
    confirm_invoice,
    cancel_invoice,
    mark_overdue_invoices,
)
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _customer_id_for_user(user) -> int | None:
    if user.role == ROLE_CUSTOMER:
        linked = Customer.query.filter_by(user_id=user.id).first()
        return linked.id if linked else None
    return None


@invoices_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_invoices():
    """List invoices — customers see only their own."""
    page, per_page = get_pagination_params()
    query = Invoice.query

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

    subscription_id = request.args.get("subscription_id", type=int)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    query = query.order_by(Invoice.invoice_date.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Invoices retrieved")


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_invoice(invoice_id: int):
    """Retrieve invoice detail — customers may only view their own."""
    invoice = Invoice.query.get_or_404(invoice_id)

    user = g.current_user
    if user.role == ROLE_CUSTOMER:
        cid = _customer_id_for_user(user)
        if invoice.customer_id != cid:
            return api_error("FORBIDDEN", "Access denied to this invoice", status_code=403)

    data = invoice.to_dict()
    # Include payment allocations summary for detail view
    data["payment_allocations"] = [
        {
            "id": pa.id,
            "payment_id": pa.payment_id,
            "allocated_amount": float(pa.allocated_amount) if pa.allocated_amount else 0.0,
        }
        for pa in invoice.payment_allocations
    ]
    return api_response(data=data, message="Invoice retrieved")


@invoices_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_invoice_route():
    """Manually create an invoice (admin/staff only)."""
    data = request.get_json(silent=True) or {}
    invoice, err = create_invoice_manual(data, g.current_user)
    if err:
        return err
    return api_response(data=invoice.to_dict(), message="Invoice created", status_code=201)


@invoices_bp.route("/<int:invoice_id>/confirm", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def confirm_invoice_route(invoice_id: int):
    """Confirm a draft invoice → posted (admin/staff only)."""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice, err = confirm_invoice(invoice, g.current_user)
    if err:
        return err
    return api_response(data=invoice.to_dict(), message="Invoice confirmed and posted")


@invoices_bp.route("/<int:invoice_id>/cancel", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def cancel_invoice_route(invoice_id: int):
    """Cancel a draft or posted invoice (admin/staff only — paid invoices cannot be cancelled)."""
    invoice = Invoice.query.get_or_404(invoice_id)
    invoice, err = cancel_invoice(invoice, g.current_user)
    if err:
        return err
    return api_response(data=invoice.to_dict(), message="Invoice cancelled")


@invoices_bp.route("/mark-overdue", methods=["POST"])
@role_required(ROLE_ADMIN)
def mark_overdue_route():
    """Admin utility: mark all past-due posted/partial invoices as overdue."""
    count = mark_overdue_invoices()
    return api_response(data={"marked_overdue": count}, message=f"{count} invoices marked overdue")
