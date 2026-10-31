"""
Invoice Service — SubFlow Member 3
Handles invoice creation, number generation, status transitions,
and payment-status updates (called by Member 4 after allocations).
All monetary arithmetic uses Python Decimal.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models.invoice import Invoice, InvoiceLine
from backend.models.subscription import Subscription
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.utils.response import api_error

TAX_RATE = Decimal("0.18")  # 18 % GST — must match quotation_service.TAX_RATE


def _next_number() -> str:
    """Generate a unique invoice number: INV-YYYYMMDD-NNNN."""
    today = date.today().strftime("%Y%m%d")
    prefix = f"INV-{today}-"
    last = (
        Invoice.query
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.invoice_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def compute_invoice_totals(lines_data: list[dict]) -> dict:
    """
    Compute invoice totals from line-item dicts.
    Each dict: { quantity, unit_price, discount_percent }.
    Returns: subtotal, discount_amount, tax_amount, total_amount, balance_due.
    """
    subtotal = Decimal("0.00")
    discount_amount = Decimal("0.00")

    for ld in lines_data:
        qty = Decimal(str(ld.get("quantity", 1)))
        price = Decimal(str(ld.get("unit_price", 0)))
        disc_pct = Decimal(str(ld.get("discount_percent", 0)))
        gross = (qty * price).quantize(Decimal("0.01"), ROUND_HALF_UP)
        disc = (gross * disc_pct / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        subtotal += gross
        discount_amount += disc

    taxable = (subtotal - discount_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
    tax_amount = (taxable * TAX_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_amount = (taxable + tax_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "balance_due": total_amount,
    }


def create_invoice_from_subscription(
    subscription: Subscription,
    as_of_date: date = None,
) -> tuple[Invoice | None, tuple | None]:
    """
    Generate an invoice for a subscription billing period.
    Idempotent: the unique constraint on (subscription_id, billing_period_start)
    prevents duplicate invoices for the same period.
    Returns (invoice, None) or (None, error_response).
    """
    as_of_date = as_of_date or date.today()
    customer = subscription.customer
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end

    if not subscription.lines:
        return None, api_error("NO_LINES", "Subscription has no line items to invoice", status_code=422)

    payment_terms_days = customer.payment_terms_days if customer else 30
    due_date = as_of_date + timedelta(days=payment_terms_days)

    lines_data = [
        {
            "product_id": sl.product_id,
            "description": sl.description,
            "quantity": float(sl.quantity),
            "unit_price": float(sl.unit_price),
            "discount_percent": float(sl.discount_percent),
        }
        for sl in subscription.lines
    ]
    totals = compute_invoice_totals(lines_data)

    invoice = Invoice(
        invoice_number=_next_number(),
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        status="draft",
        invoice_date=as_of_date,
        due_date=due_date,
        billing_period_start=period_start,
        billing_period_end=period_end,
        currency=subscription.currency or "USD",
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        tax_amount=totals["tax_amount"],
        total_amount=totals["total_amount"],
        amount_paid=Decimal("0.00"),
        balance_due=totals["balance_due"],
        payment_terms=f"Net {payment_terms_days}",
        notes=f"Auto-generated for subscription {subscription.subscription_number} "
              f"period {period_start} – {period_end}",
    )

    for ld in lines_data:
        qty = Decimal(str(ld["quantity"]))
        price = Decimal(str(ld["unit_price"]))
        disc = Decimal(str(ld["discount_percent"]))
        gross = (qty * price).quantize(Decimal("0.01"), ROUND_HALF_UP)
        disc_amt = (gross * disc / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        line_total = (gross - disc_amt).quantize(Decimal("0.01"), ROUND_HALF_UP)
        invoice.lines.append(InvoiceLine(
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=qty,
            unit_price=price,
            discount_percent=disc,
            line_total=line_total,
        ))

    db.session.add(invoice)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        # Duplicate period — safely return the existing invoice
        existing = Invoice.query.filter_by(
            subscription_id=subscription.id,
            billing_period_start=period_start
        ).first()
        return existing, None

    db.session.commit()
    return invoice, None


def create_invoice_manual(data: dict, current_user) -> tuple[Invoice | None, tuple | None]:
    """
    Create a manual invoice (admin/staff).
    Returns (invoice, None) or (None, error_response).
    """
    customer_id = data.get("customer_id")
    lines_data = data.get("lines", [])
    due_str = data.get("due_date")
    invoice_date_str = data.get("invoice_date") or date.today().isoformat()

    if not customer_id:
        return None, api_error("MISSING_FIELD", "customer_id is required", status_code=422)
    if not lines_data:
        return None, api_error("MISSING_FIELD", "At least one line item is required", status_code=422)
    if not due_str:
        return None, api_error("MISSING_FIELD", "due_date is required", status_code=422)

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None, api_error("NOT_FOUND", f"Customer {customer_id} not found", status_code=404)

    try:
        invoice_date = date.fromisoformat(invoice_date_str)
        due_date = date.fromisoformat(due_str)
    except ValueError:
        return None, api_error("INVALID_DATE", "Dates must be ISO 8601 format (YYYY-MM-DD)", status_code=422)

    if due_date < invoice_date:
        return None, api_error("INVALID_DATE_RANGE", "due_date cannot be before invoice_date", status_code=422)

    # Validate lines
    for idx, ld in enumerate(lines_data):
        if not ld.get("description"):
            return None, api_error("MISSING_FIELD", f"Line {idx + 1}: description is required", status_code=422)
        if Decimal(str(ld.get("unit_price", 0))) < 0:
            return None, api_error("INVALID_PRICE", f"Line {idx + 1}: unit_price cannot be negative", status_code=422)

    totals = compute_invoice_totals(lines_data)
    subscription_id = data.get("subscription_id")

    invoice = Invoice(
        invoice_number=_next_number(),
        customer_id=customer_id,
        subscription_id=subscription_id,
        status="draft",
        invoice_date=invoice_date,
        due_date=due_date,
        currency=customer.currency or "USD",
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        tax_amount=totals["tax_amount"],
        total_amount=totals["total_amount"],
        amount_paid=Decimal("0.00"),
        balance_due=totals["balance_due"],
        payment_terms=data.get("payment_terms", f"Net {customer.payment_terms_days}"),
        notes=data.get("notes"),
    )

    for ld in lines_data:
        qty = Decimal(str(ld.get("quantity", 1)))
        price = Decimal(str(ld.get("unit_price", 0)))
        disc = Decimal(str(ld.get("discount_percent", 0)))
        gross = (qty * price).quantize(Decimal("0.01"), ROUND_HALF_UP)
        disc_amt = (gross * disc / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        line_total = (gross - disc_amt).quantize(Decimal("0.01"), ROUND_HALF_UP)
        invoice.lines.append(InvoiceLine(
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=qty,
            unit_price=price,
            discount_percent=disc,
            line_total=line_total,
        ))

    db.session.add(invoice)
    db.session.flush()
    _audit(current_user.id, "CREATE", "invoice", invoice.id, {"number": invoice.invoice_number})
    db.session.commit()
    return invoice, None


def confirm_invoice(invoice: Invoice, current_user) -> tuple[Invoice | None, tuple | None]:
    """Transition invoice draft → posted."""
    if invoice.status != "draft":
        return None, api_error(
            "INVALID_STATUS",
            f"Only draft invoices can be confirmed. Current: {invoice.status}",
            status_code=422
        )
    invoice.status = "posted"
    _audit(current_user.id, "CONFIRM", "invoice", invoice.id, {})
    db.session.commit()
    return invoice, None


def cancel_invoice(invoice: Invoice, current_user) -> tuple[Invoice | None, tuple | None]:
    """Transition invoice draft/posted → cancelled. Cannot cancel paid invoices."""
    if invoice.status == "paid":
        return None, api_error("INVALID_STATUS", "A paid invoice cannot be cancelled", status_code=422)
    if invoice.status == "cancelled":
        return None, api_error("INVALID_STATUS", "Invoice is already cancelled", status_code=422)
    if invoice.status not in ("draft", "posted", "overdue", "partial"):
        return None, api_error(
            "INVALID_STATUS",
            f"Cannot cancel invoice with status '{invoice.status}'",
            status_code=422
        )
    invoice.status = "cancelled"
    _audit(current_user.id, "CANCEL", "invoice", invoice.id, {})
    db.session.commit()
    return invoice, None


def update_invoice_payment_status(invoice: Invoice) -> Invoice:
    """
    Recompute amount_paid and balance_due from committed payment allocations.
    Called by Member 4 (payment service) after recording an allocation.
    Sets status to 'paid', 'partial', or 'posted'/'overdue' accordingly.
    """
    total_allocated = sum(
        Decimal(str(pa.allocated_amount))
        for pa in invoice.payment_allocations
        if pa.allocated_amount
    )
    total_allocated = total_allocated.quantize(Decimal("0.01"), ROUND_HALF_UP)
    total = Decimal(str(invoice.total_amount))
    balance = (total - total_allocated).quantize(Decimal("0.01"), ROUND_HALF_UP)

    invoice.amount_paid = total_allocated
    invoice.balance_due = max(balance, Decimal("0.00"))

    if total_allocated >= total:
        invoice.status = "paid"
    elif total_allocated > 0:
        invoice.status = "partial"
    else:
        # Revert to overdue if past due, otherwise posted
        if invoice.status not in ("draft", "cancelled"):
            invoice.status = "overdue" if date.today() > invoice.due_date else "posted"

    db.session.commit()
    return invoice


def mark_overdue_invoices() -> int:
    """Bulk-mark posted/partial invoices past their due_date as 'overdue'."""
    today = date.today()
    stale = Invoice.query.filter(
        Invoice.due_date < today,
        Invoice.status.in_(["posted", "partial"])
    ).all()
    for inv in stale:
        inv.status = "overdue"
    db.session.commit()
    return len(stale)


def _audit(actor_id: int, action: str, entity_type: str, entity_id: int, meta: dict = None):
    try:
        db.session.add(AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=meta or {},
        ))
    except Exception:
        pass
