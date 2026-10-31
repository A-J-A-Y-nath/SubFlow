"""
Subscription Service — SubFlow Member 3
Handles subscription creation, status transitions, renewals, and total computation.
All monetary arithmetic uses Python Decimal for precision.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

from backend.extensions import db
from backend.models.subscription import Subscription, SubscriptionLine
from backend.models.plan import Plan
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.utils.response import api_error

# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
    "draft":     {"active", "cancelled"},
    "active":    {"paused", "cancelled", "expired"},
    "paused":    {"active", "cancelled", "expired"},
    "cancelled": set(),
    "expired":   set(),
}

# Only admin/staff may drive these transitions (customers never mutate status)
STAFF_ONLY_TRANSITIONS = {
    ("draft", "active"),
    ("active", "paused"),
    ("active", "cancelled"),
    ("active", "expired"),
    ("paused", "active"),
    ("paused", "cancelled"),
    ("paused", "expired"),
}


def _next_number() -> str:
    """Generate a unique subscription number: SUB-YYYYMMDD-NNNN."""
    today = date.today().strftime("%Y%m%d")
    prefix = f"SUB-{today}-"
    last = (
        Subscription.query
        .filter(Subscription.subscription_number.like(f"{prefix}%"))
        .order_by(Subscription.subscription_number.desc())
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.subscription_number.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


def _compute_period_end(start: date, interval: str, count: int) -> date:
    """Compute the end date of a billing period."""
    interval = interval.lower()
    if interval == "daily":
        return start + timedelta(days=count)
    if interval == "weekly":
        return start + timedelta(weeks=count)
    if interval == "monthly":
        return start + relativedelta(months=count)
    if interval == "yearly":
        return start + relativedelta(years=count)
    # Fallback: monthly
    return start + relativedelta(months=1)


def compute_subscription_totals(lines: list[dict]) -> dict:
    """
    Calculate subscription totals from line-item dicts.
    Each dict must have: quantity, unit_price, discount_percent (optional).
    Returns: subtotal, total (same for subscriptions — tax handled on invoice).
    """
    subtotal = Decimal("0.00")
    for line in lines:
        qty = Decimal(str(line.get("quantity", 1)))
        price = Decimal(str(line.get("unit_price", 0)))
        disc = Decimal(str(line.get("discount_percent", 0)))
        line_total = (qty * price * (1 - disc / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        subtotal += line_total
    return {
        "subtotal": subtotal,
        "recurring_amount": subtotal,
    }


def create_subscription(data: dict, current_user) -> tuple[Subscription | None, tuple | None]:
    """
    Create a new Subscription with SubscriptionLines.
    Returns (subscription, None) on success or (None, error_response) on failure.
    """
    plan_id = data.get("plan_id")
    customer_id = data.get("customer_id")
    start_str = data.get("start_date")
    lines_data = data.get("lines", [])

    # --- Validation ---
    if not plan_id:
        return None, api_error("MISSING_FIELD", "plan_id is required", status_code=422)
    if not customer_id:
        return None, api_error("MISSING_FIELD", "customer_id is required", status_code=422)
    if not start_str:
        return None, api_error("MISSING_FIELD", "start_date is required", status_code=422)
    if not lines_data:
        return None, api_error("MISSING_FIELD", "At least one subscription line is required", status_code=422)

    plan = db.session.get(Plan, plan_id)
    if not plan:
        return None, api_error("NOT_FOUND", f"Plan {plan_id} not found", status_code=404)
    if not plan.is_active:
        return None, api_error("INVALID_PLAN", "Selected plan is inactive", status_code=422)

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return None, api_error("NOT_FOUND", f"Customer {customer_id} not found", status_code=404)
    if not customer.is_active:
        return None, api_error("INVALID_CUSTOMER", "Customer account is inactive", status_code=422)

    try:
        start_date = date.fromisoformat(start_str)
    except ValueError:
        return None, api_error("INVALID_DATE", "start_date must be ISO 8601 format (YYYY-MM-DD)", status_code=422)

    period_end = _compute_period_end(start_date, plan.billing_interval, plan.billing_interval_count)
    next_billing = period_end  # Bill at the end of each period

    # --- Build lines ---
    sub_lines = []
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
        recurring = (qty * price * (1 - disc / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        sub_lines.append(SubscriptionLine(
            product_id=ld["product_id"],
            product_variant_id=ld.get("product_variant_id"),
            description=ld.get("description") or f"Product #{ld['product_id']}",
            quantity=qty,
            unit_price=price,
            discount_percent=disc,
            recurring_amount=recurring,
        ))

    totals = compute_subscription_totals(lines_data)

    sub = Subscription(
        subscription_number=_next_number(),
        customer_id=customer_id,
        plan_id=plan_id,
        quotation_id=data.get("quotation_id"),
        status="draft",
        start_date=start_date,
        current_period_start=start_date,
        current_period_end=period_end,
        next_billing_date=next_billing,
        auto_renew=data.get("auto_renew", True),
        recurring_amount=totals["recurring_amount"],
        currency=customer.currency or plan.currency or "USD",
    )
    for line in sub_lines:
        sub.lines.append(line)

    db.session.add(sub)
    db.session.flush()

    _audit(current_user.id, "CREATE", "subscription", sub.id, {"number": sub.subscription_number})
    db.session.commit()
    return sub, None


def update_subscription_status(
    subscription: Subscription,
    new_status: str,
    current_user,
    reason: str = None
) -> tuple[Subscription | None, tuple | None]:
    """
    Validate and apply a subscription status transition.
    Returns (subscription, None) on success or (None, error_response).
    """
    old_status = subscription.status
    allowed = VALID_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        return None, api_error(
            "INVALID_TRANSITION",
            f"Cannot transition from '{old_status}' to '{new_status}'. "
            f"Allowed: {sorted(allowed) or 'none'}",
            status_code=422
        )

    plan = subscription.plan
    if new_status == "paused" and plan and not getattr(plan, "can_pause", True):
        return None, api_error("PLAN_RESTRICTION", "This plan does not allow pausing", status_code=422)

    subscription.status = new_status
    if new_status == "cancelled":
        from datetime import datetime, timezone
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.cancel_reason = reason

    _audit(current_user.id, "STATUS_CHANGE", "subscription", subscription.id, {
        "old_status": old_status, "new_status": new_status, "reason": reason
    })
    db.session.commit()
    return subscription, None


def renew_subscription(subscription: Subscription, current_user) -> tuple[Subscription | None, tuple | None]:
    """
    Renew a subscription: advance billing period and re-activate if needed.
    """
    if subscription.status not in ("active", "paused", "expired"):
        return None, api_error(
            "INVALID_TRANSITION",
            f"Cannot renew a subscription with status '{subscription.status}'",
            status_code=422
        )
    plan = subscription.plan
    new_start = subscription.current_period_end
    new_end = _compute_period_end(new_start, plan.billing_interval, plan.billing_interval_count)

    subscription.current_period_start = new_start
    subscription.current_period_end = new_end
    subscription.next_billing_date = new_end
    if subscription.status in ("paused", "expired"):
        subscription.status = "active"

    _audit(current_user.id, "RENEW", "subscription", subscription.id, {
        "new_period_start": new_start.isoformat(),
        "new_period_end": new_end.isoformat(),
    })
    db.session.commit()
    return subscription, None


def _audit(actor_id: int, action: str, entity_type: str, entity_id: int, meta: dict = None):
    """Write an audit log entry (best-effort; don't raise)."""
    try:
        log = AuditLog(
            user_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            new_values=meta or {},
        )
        db.session.add(log)
    except Exception:
        pass
