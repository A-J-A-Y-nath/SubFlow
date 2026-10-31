from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from flask import Blueprint, request, g
from sqlalchemy import or_
from backend.extensions import db
from backend.models.invoice import Invoice, InvoiceLine
from backend.models.customer import Customer
from backend.models.subscription import Subscription
from backend.models.audit_log import AuditLog
from backend.services.billing_service import BillingService
from backend.services.analytics_service import AnalyticsService
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _get_customer_id_for_current_user() -> int | None:
    """Helper to retrieve the authenticated customer's customer_id safely."""
    if not hasattr(g, "current_user") or not g.current_user:
        return None
    if g.current_user.role == ROLE_CUSTOMER:
        return g.current_user.customer_profile.id if g.current_user.customer_profile else -1
    return None


@invoices_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_invoices():
    """
    List invoices with filtering by status, customer, subscription, search, and date.
    Enforces customer isolation (customers only see their own invoices).
    """
    page, per_page = get_pagination_params()
    query = Invoice.query

    # Enforce customer data isolation
    customer_id_override = _get_customer_id_for_current_user()
    if customer_id_override is not None:
        query = query.filter_by(customer_id=customer_id_override)
    else:
        # Staff/Admin can filter by customer_id
        customer_id_param = request.args.get("customer_id", type=int)
        if customer_id_param:
            query = query.filter_by(customer_id=customer_id_param)

    # Status filter
    status = request.args.get("status")
    if status and status.lower() != "all":
        query = query.filter_by(status=status.lower())

    # Subscription filter
    subscription_id = request.args.get("subscription_id", type=int)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    # Overdue filter
    is_overdue = request.args.get("is_overdue")
    if is_overdue and is_overdue.lower() in ("true", "1"):
        today = date.today()
        query = query.filter(
            or_(
                Invoice.status == "overdue",
                (Invoice.status.in_(["posted", "partial"])) & (Invoice.due_date < today) & (Invoice.balance_due > 0)
            )
        )

    # Search filter (invoice_number or customer name)
    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.outerjoin(Customer).filter(
            or_(
                Invoice.invoice_number.ilike(search_pattern),
                Customer.company_name.ilike(search_pattern)
            )
        )

    query = query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Invoices retrieved successfully")


@invoices_bp.route("/customers", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def get_invoicing_customers():
    """List customers for invoice selection dropdown."""
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name.asc()).all()
    return api_response(data=[c.to_dict() for c in customers], message="Customers retrieved")


@invoices_bp.route("/active-subscriptions", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def get_invoicing_subscriptions():
    """List active subscriptions for quick invoice generation."""
    customer_id = request.args.get("customer_id", type=int)
    query = Subscription.query.filter_by(status="active")
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    subs = query.order_by(Subscription.id.desc()).all()
    return api_response(data=[s.to_dict() for s in subs], message="Subscriptions retrieved")


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_invoice(invoice_id: int):
    """
    Retrieve detailed invoice view with line items and allocations.
    Protects customer data against unauthorized cross-tenant access.
    """
    invoice = Invoice.query.get_or_404(invoice_id)

    # RBAC Customer isolation
    cust_id = _get_customer_id_for_current_user()
    if cust_id is not None and invoice.customer_id != cust_id:
        return api_error(
            code="FORBIDDEN",
            message="You are not authorized to view this invoice",
            status_code=403
        )

    invoice_data = invoice.to_dict()
    # Add detailed allocations list
    invoice_data["allocations"] = [
        {
            "id": a.id,
            "payment_id": a.payment_id,
            "payment_number": a.payment.payment_number if a.payment else None,
            "payment_date": a.payment.payment_date.isoformat() if a.payment and a.payment.payment_date else None,
            "payment_method": a.payment.payment_method if a.payment else None,
            "amount_allocated": float(a.amount_allocated),
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in invoice.payment_allocations
    ]
    return api_response(data=invoice_data, message="Invoice details retrieved")


@invoices_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_invoice():
    """
    Manual invoice creation endpoint for staff and administrators.
    Recalculates all monetary figures on the backend.
    """
    data = request.get_json(silent=True) or {}

    customer_id = data.get("customer_id")
    if not customer_id:
        return api_error(code="VALIDATION_ERROR", message="Customer ID is required", status_code=422)

    lines = data.get("lines")
    if not lines or not isinstance(lines, list) or len(lines) == 0:
        return api_error(code="VALIDATION_ERROR", message="At least one invoice line item is required", status_code=422)

    # Dates
    try:
        inv_date = date.fromisoformat(data["invoice_date"]) if data.get("invoice_date") else date.today()
    except (ValueError, TypeError):
        return api_error(code="INVALID_DATE", message="Invalid invoice_date format (expected YYYY-MM-DD)", status_code=422)

    try:
        due_date = date.fromisoformat(data["due_date"]) if data.get("due_date") else inv_date + timedelta(days=30)
    except (ValueError, TypeError):
        return api_error(code="INVALID_DATE", message="Invalid due_date format (expected YYYY-MM-DD)", status_code=422)

    tax_amount = Decimal(str(data.get("tax_amount", 0)))
    status = (data.get("status") or "draft").lower()
    if status not in ("draft", "posted"):
        status = "draft"

    try:
        invoice = BillingService.create_invoice(
            customer_id=int(customer_id),
            invoice_date=inv_date,
            due_date=due_date,
            lines=lines,
            subscription_id=data.get("subscription_id"),
            quotation_id=data.get("quotation_id"),
            coupon_code=data.get("coupon_code"),
            tax_amount=tax_amount,
            notes=data.get("notes"),
            payment_terms=data.get("payment_terms") or "Net 30",
            currency=data.get("currency") or "USD",
            status=status,
            user_id=g.current_user.id
        )
        db.session.commit()
        return api_response(data=invoice.to_dict(), message="Invoice created successfully", status_code=201)
    except ValueError as ve:
        db.session.rollback()
        return api_error(code="VALIDATION_ERROR", message=str(ve), status_code=422)
    except Exception as e:
        db.session.rollback()
        return api_error(code="INTERNAL_SERVER_ERROR", message=str(e), status_code=500)


@invoices_bp.route("/<int:invoice_id>/issue", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def issue_invoice(invoice_id: int):
    """
    Transition invoice from draft to posted (issued).
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.status != "draft":
        return api_error(
            code="INVALID_STATUS_TRANSITION",
            message=f"Only draft invoices can be issued. Current status: '{invoice.status}'",
            status_code=400
        )

    invoice.status = "posted"
    audit = AuditLog(
        user_id=g.current_user.id,
        action="INVOICE_ISSUED",
        entity_type="Invoice",
        entity_id=str(invoice.id),
        old_values={"status": "draft"},
        new_values={"status": "posted", "invoice_number": invoice.invoice_number}
    )
    db.session.add(audit)
    db.session.commit()
    return api_response(data=invoice.to_dict(), message=f"Invoice {invoice.invoice_number} has been posted successfully")


@invoices_bp.route("/<int:invoice_id>/cancel", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def cancel_invoice(invoice_id: int):
    """
    Cancel an unpaid draft or posted invoice.
    Invoices with recorded payments cannot be cancelled.
    """
    invoice = Invoice.query.get_or_404(invoice_id)
    if invoice.status == "cancelled":
        return api_error(code="ALREADY_CANCELLED", message="Invoice is already cancelled", status_code=400)

    if invoice.status == "paid" or (invoice.amount_paid and invoice.amount_paid > Decimal("0.00")):
        return api_error(
            code="CANNOT_CANCEL_PAID_INVOICE",
            message="Cannot cancel an invoice with payments allocated to it. Refund payments first.",
            status_code=400
        )

    old_status = invoice.status
    invoice.status = "cancelled"
    audit = AuditLog(
        user_id=g.current_user.id,
        action="INVOICE_CANCELLED",
        entity_type="Invoice",
        entity_id=str(invoice.id),
        old_values={"status": old_status},
        new_values={"status": "cancelled", "invoice_number": invoice.invoice_number}
    )
    db.session.add(audit)
    db.session.commit()
    return api_response(data=invoice.to_dict(), message=f"Invoice {invoice.invoice_number} has been cancelled")


@invoices_bp.route("/from-subscription/<int:subscription_id>", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def generate_from_subscription(subscription_id: int):
    """
    Generates an invoice directly from an active subscription record.
    """
    sub = db.session.get(Subscription, subscription_id)
    if not sub:
        return api_error(code="NOT_FOUND", message="Subscription not found", status_code=404)

    if sub.status != "active":
        return api_error(
            code="INELIGIBLE_SUBSCRIPTION",
            message=f"Only active subscriptions can generate invoices. Current status: '{sub.status}'",
            status_code=400
        )

    customer = sub.customer
    inv_date = date.today()
    due_date = inv_date + timedelta(days=customer.payment_terms_days or 30)

    lines = []
    if sub.lines and len(sub.lines) > 0:
        for sl in sub.lines:
            lines.append({
                "product_id": sl.product_id,
                "description": sl.description or f"{sub.plan.name} Item",
                "quantity": sl.quantity,
                "unit_price": sl.unit_price,
                "discount_percent": sl.discount_percent
            })
    else:
        lines.append({
            "product_id": None,
            "description": f"{sub.plan.name} Recurring Service",
            "quantity": 1,
            "unit_price": float(sub.recurring_amount or sub.plan.base_price),
            "discount_percent": 0
        })

    try:
        invoice = BillingService.create_invoice(
            customer_id=sub.customer_id,
            invoice_date=inv_date,
            due_date=due_date,
            lines=lines,
            subscription_id=sub.id,
            quotation_id=sub.quotation_id,
            status="posted",
            currency=sub.currency or "USD",
            payment_terms=f"Net {customer.payment_terms_days or 30}",
            notes=f"Generated from subscription {sub.subscription_number}",
            user_id=g.current_user.id
        )
        db.session.commit()
        return api_response(data=invoice.to_dict(), message="Invoice generated from subscription", status_code=201)
    except Exception as e:
        db.session.rollback()
        return api_error(code="GENERATION_FAILED", message=str(e), status_code=500)


@invoices_bp.route("/recurring-billing/run", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def run_recurring_billing():
    """
    Executes the automated recurring billing engine to process all subscriptions due.
    """
    data = request.get_json(silent=True) or {}
    target_date_str = data.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
    dry_run = bool(data.get("dry_run", False))

    results = BillingService.generate_recurring_invoices(
        target_date=target_date,
        dry_run=dry_run,
        user_id=g.current_user.id
    )
    return api_response(data=results, message="Recurring billing job completed successfully")


@invoices_bp.route("/recurring-billing/preview", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def preview_recurring_billing():
    """
    Preview eligible subscriptions that would be invoiced by the recurring billing engine.
    """
    target_date_str = request.args.get("target_date")
    target_date = date.fromisoformat(target_date_str) if target_date_str else date.today()

    results = BillingService.generate_recurring_invoices(
        target_date=target_date,
        dry_run=True,
        user_id=g.current_user.id
    )
    return api_response(data=results, message="Recurring billing preview generated")


@invoices_bp.route("/receivables/summary", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_receivables_summary():
    """
    Returns summary statistics for receivables, aging buckets, and overdue totals.
    """
    customer_id = _get_customer_id_for_current_user()
    summary = AnalyticsService.get_financial_summary(customer_id=customer_id)
    aging = AnalyticsService.get_aging_report(customer_id=customer_id)
    return api_response(
        data={"summary": summary, "aging": aging},
        message="Receivables summary loaded successfully"
    )
