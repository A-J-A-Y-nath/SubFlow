"""
Invoices Routes — SubFlow
Full lifecycle: list, create, detail, issue/confirm, cancel, recurring billing, and receivables analytics.
Customers see only their own invoices.
"""
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
try:
    from backend.services.invoice_service import mark_overdue_invoices
except ImportError:
    mark_overdue_invoices = None
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


def _customer_id_for_user(user) -> int | None:
    if not user:
        return None
    if user.role == ROLE_CUSTOMER:
        if hasattr(user, "customer_profile") and user.customer_profile:
            return user.customer_profile.id
        linked = Customer.query.filter_by(user_id=user.id).first()
        return linked.id if linked else -1
    return None


def _get_customer_id_for_current_user() -> int | None:
    return _customer_id_for_user(getattr(g, "current_user", None))


@invoices_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_invoices():
    page, per_page = get_pagination_params()
    query = Invoice.query

    user = g.current_user
    if user.role == ROLE_CUSTOMER:
        cid = _customer_id_for_user(user)
        if cid is None or cid == -1:
            return api_response(data={"items": [], "total": 0, "page": page, "per_page": per_page, "pages": 0}, message="No customer profile linked")
        query = query.filter_by(customer_id=cid)
    else:
        customer_id_param = request.args.get("customer_id", type=int)
        if customer_id_param:
            query = query.filter_by(customer_id=customer_id_param)

    status = request.args.get("status")
    if status and status.lower() != "all":
        query = query.filter_by(status=status.lower())

    subscription_id = request.args.get("subscription_id", type=int)
    if subscription_id:
        query = query.filter_by(subscription_id=subscription_id)

    is_overdue = request.args.get("is_overdue")
    if is_overdue and is_overdue.lower() in ("true", "1"):
        today = date.today()
        query = query.filter(
            or_(
                Invoice.status == "overdue",
                (Invoice.status.in_(["posted", "partial"])) & (Invoice.due_date < today) & (Invoice.balance_due > 0)
            )
        )

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
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.company_name.asc()).all()
    return api_response(data=[c.to_dict() for c in customers], message="Customers retrieved")


@invoices_bp.route("/active-subscriptions", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def get_invoicing_subscriptions():
    customer_id = request.args.get("customer_id", type=int)
    query = Subscription.query.filter_by(status="active")
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    subs = query.order_by(Subscription.id.desc()).all()
    return api_response(data=[s.to_dict() for s in subs], message="Subscriptions retrieved")


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_invoice(invoice_id: int):
    invoice = Invoice.query.get_or_404(invoice_id)
    user = g.current_user
    if user.role == ROLE_CUSTOMER:
        cid = _customer_id_for_user(user)
        if invoice.customer_id != cid:
            return api_error("FORBIDDEN", "Access denied to this invoice", status_code=403)

    data = invoice.to_dict()
    allocations_list = [
        {
            "id": a.id,
            "payment_id": a.payment_id,
            "payment_number": a.payment.payment_number if a.payment else None,
            "payment_date": a.payment.payment_date.isoformat() if a.payment and a.payment.payment_date else None,
            "payment_method": a.payment.payment_method if a.payment else None,
            "amount_allocated": float(a.amount_allocated),
            "allocated_amount": float(a.amount_allocated),
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in invoice.payment_allocations
    ]
    data["allocations"] = allocations_list
    data["payment_allocations"] = allocations_list
    return api_response(data=data, message="Invoice details retrieved")


@invoices_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_invoice():
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    if not customer_id:
        return api_error(code="VALIDATION_ERROR", message="Customer ID is required", status_code=422)

    lines = data.get("lines")
    if not lines or not isinstance(lines, list) or len(lines) == 0:
        return api_error(code="VALIDATION_ERROR", message="At least one invoice line item is required", status_code=422)

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
@invoices_bp.route("/<int:invoice_id>/confirm", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def issue_invoice(invoice_id: int):
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
    customer_id = _get_customer_id_for_current_user()
    summary = AnalyticsService.get_financial_summary(customer_id=customer_id)
    aging = AnalyticsService.get_aging_report(customer_id=customer_id)
    return api_response(
        data={"summary": summary, "aging": aging},
        message="Receivables summary loaded successfully"
    )


@invoices_bp.route("/mark-overdue", methods=["POST"])
@role_required(ROLE_ADMIN)
def mark_overdue_route():
    if mark_overdue_invoices:
        count = mark_overdue_invoices()
    else:
        today = date.today()
        overdue_invs = Invoice.query.filter(
            Invoice.status.in_(["posted", "partial"]),
            Invoice.due_date < today,
            Invoice.balance_due > 0
        ).all()
        for inv in overdue_invs:
            inv.status = "overdue"
        db.session.commit()
        count = len(overdue_invs)
    return api_response(data={"marked_overdue": count}, message=f"{count} invoices marked overdue")