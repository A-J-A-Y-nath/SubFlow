"""
Quotation Service — SubFlow Member 3
Handles quotation creation, number generation, total calculation,
status transitions, and conversion to subscriptions.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from backend.extensions import db
from backend.models.quotation import Quotation, QuotationLine
from backend.models.customer import Customer
from backend.models.plan import Plan
from backend.models.audit_log import AuditLog
from backend.utils.response import api_error

TAX_RATE = Decimal("0.18")  # 18 % GST — configurable here, applied consistently


def _next_number() -> str:
    """Generate a unique quotation number: QUO-YYYYMMDD-NNNN."""
    today = date.today().strftime("%Y%m%d")
    prefix = f"QUO-{today}-"
    last = (
        Quotation.query
        .filter(Quotation.quotation_number.like(f"{prefix}%"))
        .order_by(Quotation.quotation_number.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.quotation_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def compute_quotation_totals(lines_data: list[dict]) -> dict:
    """
    Compute subtotal, discount_amount, tax_amount, total_amount from line items.
    Each line dict: { quantity, unit_price, discount_percent }.
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
    }


def create_quotation(data: dict, current_user) -> tuple[Quotation | None, tuple | None]:
    """
    Create a Quotation with QuotationLines.
    Returns (quotation, None) or (None, error_response).
    """
    customer_id = data.get("customer_id")
    plan_id = data.get("plan_id")
    issue_str = data.get("issue_date")
    valid_str = data.get("valid_until")
    lines_data = data.get("lines", [])

    if not customer_id:
        return None, api_error("MISSING_FIELD", "customer_id is required", status_code=422)
    if not issue_str:
        return None, api_error("MISSING_FIELD", "issue_date is required", status_code=422)
    if not valid_str:
        return None, api_error("MISSING_FIELD", "valid_until is required", status_code=422)
    if not lines_data:
        return None, api_error("MISSING_FIELD", "At least one line item is required", status_code=422)

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None, api_error("NOT_FOUND", f"Customer {customer_id} not found", status_code=404)

    if plan_id:
        plan = db.session.get(Plan, plan_id)
        if not plan:
            return None, api_error("NOT_FOUND", f"Plan {plan_id} not found", status_code=404)

    try:
        issue_date = date.fromisoformat(issue_str)
        valid_until = date.fromisoformat(valid_str)
    except ValueError:
        return None, api_error("INVALID_DATE", "Dates must be ISO 8601 format (YYYY-MM-DD)", status_code=422)

    if valid_until <= issue_date:
        return None, api_error("INVALID_DATE_RANGE", "valid_until must be after issue_date", status_code=422)

    # Validate lines
    quo_lines = []
    for idx, ld in enumerate(lines_data):
        if not ld.get("product_id"):
            return None, api_error("MISSING_FIELD", f"Line {idx + 1}: product_id is required", status_code=422)
        qty = Decimal(str(ld.get("quantity", 1)))
        price = Decimal(str(ld.get("unit_price", 0)))
        disc = Decimal(str(ld.get("discount_percent", 0)))
        if qty <= 0:
            return None, api_error("INVALID_QUANTITY", f"Line {idx + 1}: quantity must be > 0", status_code=422)
        if price < 0:
            return None, api_error("INVALID_PRICE", f"Line {idx + 1}: unit_price cannot be negative", status_code=422)
        if not (0 <= disc <= 100):
            return None, api_error("INVALID_DISCOUNT", f"Line {idx + 1}: discount_percent must be 0–100", status_code=422)

        gross = (qty * price).quantize(Decimal("0.01"), ROUND_HALF_UP)
        disc_amt = (gross * disc / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
        line_total = (gross - disc_amt).quantize(Decimal("0.01"), ROUND_HALF_UP)

        quo_lines.append(QuotationLine(
            product_id=ld["product_id"],
            product_variant_id=ld.get("product_variant_id"),
            description=ld.get("description") or f"Product #{ld['product_id']}",
            quantity=qty,
            unit_price=price,
            discount_percent=disc,
            total_amount=line_total,
        ))

    totals = compute_quotation_totals(lines_data)

    quotation = Quotation(
        quotation_number=_next_number(),
        customer_id=customer_id,
        plan_id=plan_id,
        created_by_id=current_user.id,
        status="draft",
        issue_date=issue_date,
        valid_until=valid_until,
        currency=customer.currency or "USD",
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        tax_amount=totals["tax_amount"],
        total_amount=totals["total_amount"],
        terms_and_conditions=data.get("terms_and_conditions"),
        notes=data.get("notes"),
    )
    for line in quo_lines:
        quotation.lines.append(line)

    db.session.add(quotation)
    db.session.flush()

    _audit(current_user.id, "CREATE", "quotation", quotation.id, {"number": quotation.quotation_number})
    db.session.commit()
    return quotation, None


def update_quotation(quotation: Quotation, data: dict, current_user) -> tuple[Quotation | None, tuple | None]:
    """Update a draft quotation's fields and lines."""
    if quotation.status not in ("draft", "sent"):
        return None, api_error(
            "INVALID_STATUS",
            f"Only draft or sent quotations can be edited. Current status: {quotation.status}",
            status_code=422
        )

    if "valid_until" in data:
        try:
            valid_until = date.fromisoformat(data["valid_until"])
        except ValueError:
            return None, api_error("INVALID_DATE", "valid_until must be ISO 8601 (YYYY-MM-DD)", status_code=422)
        if valid_until <= quotation.issue_date:
            return None, api_error("INVALID_DATE_RANGE", "valid_until must be after issue_date", status_code=422)
        quotation.valid_until = valid_until

    if "notes" in data:
        quotation.notes = data["notes"]
    if "terms_and_conditions" in data:
        quotation.terms_and_conditions = data["terms_and_conditions"]
    if "plan_id" in data:
        quotation.plan_id = data["plan_id"]

    # Replace lines if provided
    if "lines" in data:
        lines_data = data["lines"]
        if not lines_data:
            return None, api_error("MISSING_FIELD", "At least one line item is required", status_code=422)
        for line in list(quotation.lines):
            db.session.delete(line)
        db.session.flush()
        for idx, ld in enumerate(lines_data):
            if not ld.get("product_id"):
                return None, api_error("MISSING_FIELD", f"Line {idx + 1}: product_id is required", status_code=422)
            qty = Decimal(str(ld.get("quantity", 1)))
            price = Decimal(str(ld.get("unit_price", 0)))
            disc = Decimal(str(ld.get("discount_percent", 0)))
            gross = (qty * price).quantize(Decimal("0.01"), ROUND_HALF_UP)
            disc_amt = (gross * disc / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
            line_total = (gross - disc_amt).quantize(Decimal("0.01"), ROUND_HALF_UP)
            quotation.lines.append(QuotationLine(
                product_id=ld["product_id"],
                product_variant_id=ld.get("product_variant_id"),
                description=ld.get("description") or f"Product #{ld['product_id']}",
                quantity=qty,
                unit_price=price,
                discount_percent=disc,
                total_amount=line_total,
            ))
        totals = compute_quotation_totals(lines_data)
        quotation.subtotal = totals["subtotal"]
        quotation.discount_amount = totals["discount_amount"]
        quotation.tax_amount = totals["tax_amount"]
        quotation.total_amount = totals["total_amount"]

    _audit(current_user.id, "UPDATE", "quotation", quotation.id, {})
    db.session.commit()
    return quotation, None


def send_quotation(quotation: Quotation, current_user) -> tuple[Quotation | None, tuple | None]:
    """Transition a draft quotation to 'sent'."""
    if quotation.status != "draft":
        return None, api_error("INVALID_STATUS", f"Only draft quotations can be sent. Current: {quotation.status}", status_code=422)
    quotation.status = "sent"
    _audit(current_user.id, "SEND", "quotation", quotation.id, {})
    db.session.commit()
    return quotation, None


def confirm_quotation(quotation: Quotation, data: dict, current_user):
    """
    Approve a quotation: transition to 'approved' and spawn a draft Subscription.
    Returns (quotation, subscription, None) or (None, None, error_response).
    """
    from backend.services.subscription_service import create_subscription

    if quotation.status not in ("draft", "sent"):
        return None, None, api_error(
            "INVALID_STATUS",
            f"Only draft or sent quotations can be confirmed. Current: {quotation.status}",
            status_code=422
        )
    if date.today() > quotation.valid_until:
        quotation.status = "expired"
        db.session.commit()
        return None, None, api_error("QUOTATION_EXPIRED", "This quotation has passed its validity date", status_code=422)

    if not quotation.plan_id:
        return None, None, api_error("MISSING_FIELD", "Quotation must have a plan before confirming", status_code=422)

    quotation.status = "approved"
    _audit(current_user.id, "CONFIRM", "quotation", quotation.id, {})

    # Build subscription lines from quotation lines
    sub_lines = [
        {
            "product_id": ql.product_id,
            "product_variant_id": ql.product_variant_id,
            "description": ql.description,
            "quantity": float(ql.quantity),
            "unit_price": float(ql.unit_price),
            "discount_percent": float(ql.discount_percent),
        }
        for ql in quotation.lines
    ]

    start_date = data.get("start_date") or date.today().isoformat()
    sub_data = {
        "plan_id": quotation.plan_id,
        "customer_id": quotation.customer_id,
        "quotation_id": quotation.id,
        "start_date": start_date,
        "lines": sub_lines,
        "auto_renew": data.get("auto_renew", True),
    }

    subscription, err = create_subscription(sub_data, current_user)
    if err:
        return None, None, err

    subscription.quotation_id = quotation.id
    db.session.commit()
    return quotation, subscription, None


def expire_stale_quotations() -> int:
    """
    Bulk-expire draft/sent quotations whose valid_until has passed.
    Returns number of records updated.
    """
    today = date.today()
    stale = Quotation.query.filter(
        Quotation.valid_until < today,
        Quotation.status.in_(["draft", "sent"])
    ).all()
    for q in stale:
        q.status = "expired"
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
