from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, g
from sqlalchemy import or_
from backend.extensions import db
from backend.models.payment import Payment, PaymentAllocation
from backend.models.invoice import Invoice
from backend.models.customer import Customer
from backend.services.payment_service import PaymentService
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


def _get_customer_id_for_current_user() -> int | None:
    if not hasattr(g, "current_user") or not g.current_user:
        return None
    if g.current_user.role == ROLE_CUSTOMER:
        return g.current_user.customer_profile.id if g.current_user.customer_profile else -1
    return None


@payments_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_payments():
    """
    List payments with method, status, search, and customer filtering.
    Enforces customer isolation (customers only see their own payment history).
    """
    page, per_page = get_pagination_params()
    query = Payment.query

    # RBAC customer isolation
    cust_id_override = _get_customer_id_for_current_user()
    if cust_id_override is not None:
        query = query.filter_by(customer_id=cust_id_override)
    else:
        customer_id = request.args.get("customer_id", type=int)
        if customer_id:
            query = query.filter_by(customer_id=customer_id)

    status = request.args.get("status")
    if status and status.lower() != "all":
        query = query.filter_by(status=status.lower())

    payment_method = request.args.get("payment_method")
    if payment_method and payment_method.lower() != "all":
        query = query.filter_by(payment_method=payment_method.lower())

    # Search filter (payment_number, transaction_reference, customer name)
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(Customer).filter(
            or_(
                Payment.payment_number.ilike(search_pattern),
                Payment.transaction_reference.ilike(search_pattern),
                Customer.company_name.ilike(search_pattern)
            )
        )

    query = query.order_by(Payment.payment_date.desc(), Payment.id.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Payments retrieved successfully")


@payments_bp.route("/<int:payment_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_payment(payment_id: int):
    """
    Retrieve detailed payment transaction with allocations and unallocated amounts.
    """
    payment = Payment.query.get_or_404(payment_id)

    # Customer isolation
    cust_id = _get_customer_id_for_current_user()
    if cust_id is not None and payment.customer_id != cust_id:
        return api_error(code="FORBIDDEN", message="You are not authorized to view this payment", status_code=403)

    summary = PaymentService.get_payment_summary(payment.id)
    return api_response(data=summary, message="Payment details retrieved")


@payments_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def record_payment():
    """
    Record customer payment receipt and optionally allocate to an invoice.
    """
    data = request.get_json(silent=True) or {}

    customer_id = data.get("customer_id")
    if not customer_id:
        return api_error(code="VALIDATION_ERROR", message="Customer ID is required", status_code=422)

    amount = data.get("amount")
    if amount is None:
        return api_error(code="VALIDATION_ERROR", message="Payment amount is required", status_code=422)

    try:
        p_date = datetime.fromisoformat(data["payment_date"]) if data.get("payment_date") else datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return api_error(code="INVALID_DATE", message="Invalid payment_date format", status_code=422)

    try:
        payment = PaymentService.record_payment(
            customer_id=int(customer_id),
            amount=amount,
            payment_method=data.get("payment_method") or "credit_card",
            status=data.get("status") or "completed",
            payment_date=p_date,
            transaction_reference=data.get("transaction_reference"),
            invoice_id=data.get("invoice_id"),
            notes=data.get("notes"),
            currency=data.get("currency") or "USD",
            user_id=g.current_user.id
        )
        db.session.commit()
        return api_response(
            data=PaymentService.get_payment_summary(payment.id),
            message="Payment recorded successfully",
            status_code=201
        )
    except ValueError as ve:
        db.session.rollback()
        return api_error(code="VALIDATION_ERROR", message=str(ve), status_code=422)
    except Exception as e:
        db.session.rollback()
        return api_error(code="PAYMENT_ERROR", message=str(e), status_code=500)


@payments_bp.route("/<int:payment_id>/allocate", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def allocate_payment(payment_id: int):
    """
    Allocates available payment funds across one or more customer invoices.
    Expects JSON body: { "allocations": [ { "invoice_id": 1, "amount": 100.00 } ] }
    """
    data = request.get_json(silent=True) or {}
    allocations = data.get("allocations")
    if not allocations or not isinstance(allocations, list):
        return api_error(code="VALIDATION_ERROR", message="Allocations list is required", status_code=422)

    try:
        result = PaymentService.allocate_payment(
            payment_id=payment_id,
            allocations=allocations,
            user_id=g.current_user.id
        )
        return api_response(data=result, message="Payment successfully allocated")
    except ValueError as ve:
        db.session.rollback()
        return api_error(code="ALLOCATION_ERROR", message=str(ve), status_code=422)
    except Exception as e:
        db.session.rollback()
        return api_error(code="INTERNAL_SERVER_ERROR", message=str(e), status_code=500)


@payments_bp.route("/invoice/<int:invoice_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_invoice_payments(invoice_id: int):
    """
    Retrieves all payment transactions and allocations for a specific invoice.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    cust_id = _get_customer_id_for_current_user()
    if cust_id is not None and invoice.customer_id != cust_id:
        return api_error(code="FORBIDDEN", message="Unauthorized access to invoice payments", status_code=403)

    allocations = (
        PaymentAllocation.query.filter_by(invoice_id=invoice.id)
        .order_by(PaymentAllocation.created_at.desc())
        .all()
    )
    result = [
        {
            "allocation_id": a.id,
            "payment_id": a.payment_id,
            "payment_number": a.payment.payment_number if a.payment else None,
            "payment_method": a.payment.payment_method if a.payment else None,
            "transaction_reference": a.payment.transaction_reference if a.payment else None,
            "payment_date": a.payment.payment_date.isoformat() if a.payment and a.payment.payment_date else None,
            "amount_allocated": float(a.amount_allocated),
            "payment_status": a.payment.status if a.payment else None
        }
        for a in allocations
    ]
    return api_response(data=result, message="Invoice payment history retrieved")
