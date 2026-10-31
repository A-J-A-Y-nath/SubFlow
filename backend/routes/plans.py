from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, g
from backend.extensions import db
from backend.models.plan import Plan
from backend.models.audit_log import AuditLog
from backend.models.subscription import Subscription
from backend.models.quotation import Quotation
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import (
    role_required,
    staff_or_admin_required,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_CUSTOMER,
)

plans_bp = Blueprint("plans", __name__, url_prefix="/plans")

VALID_INTERVALS = ("daily", "weekly", "monthly", "quarterly", "yearly")


def _parse_decimal(val, field_name="Price", min_val=0, allow_none=False):
    """Safely parse a numeric or string value to Decimal with non-negative validation."""
    if val is None:
        if allow_none:
            return None, None
        return None, f"{field_name} is required"
    try:
        dec = Decimal(str(val).strip())
        if dec < min_val:
            return None, f"{field_name} cannot be negative"
        return dec, None
    except (InvalidOperation, TypeError, ValueError):
        return None, f"{field_name} must be a valid number"


def _parse_date(date_val, field_name: str) -> tuple[str | None, str | None]:
    """Parse and validate date string in YYYY-MM-DD format."""
    if not date_val:
        return None, None
    try:
        dt = datetime.strptime(str(date_val).strip(), "%Y-%m-%d").date()
        return dt.isoformat(), None
    except ValueError:
        return None, f"{field_name} must be a valid date in YYYY-MM-DD format"


def _log_audit(action: str, entity_type: str, entity_id: str, new_values=None, old_values=None):
    """Helper to log audit events if user is authenticated in request context."""
    user = getattr(g, "current_user", None)
    user_id = user.id if user else None
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_values=old_values,
            new_values=new_values,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
        )
        db.session.add(audit)
    except Exception:
        pass


@plans_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_plans():
    """
    List subscription plans with interval filter, active status, search filter, and pagination.
    Customers only receive active plans within current availability date windows.
    """
    page, per_page = get_pagination_params(default_per_page=50)
    query = Plan.query

    current_user = getattr(g, "current_user", None)
    is_customer = current_user and current_user.role == ROLE_CUSTOMER

    # Active status filter
    if is_customer:
        query = query.filter(Plan.is_active.is_(True))
    else:
        active_filter = request.args.get("is_active")
        if active_filter is not None:
            query = query.filter(Plan.is_active == (active_filter.lower() in ("true", "1")))

    # Interval filter (e.g., 'monthly', 'yearly', 'all')
    interval = request.args.get("billing_interval", "").strip().lower()
    if interval and interval != "all":
        query = query.filter(Plan.billing_interval == interval)

    # Search filter
    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(Plan.name.ilike(f"%{search}%") | Plan.code.ilike(f"%{search}%"))

    query = query.order_by(Plan.base_price.asc())

    # If customer, also filter availability dates
    if is_customer:
        all_plans = query.all()
        today_str = date.today().isoformat()
        filtered = []
        for p in all_plans:
            p_dict = p.to_dict()
            av_from = p_dict.get("available_from")
            av_until = p_dict.get("available_until")
            if av_from and av_from > today_str:
                continue
            if av_until and av_until < today_str:
                continue
            filtered.append(p_dict)

        total = len(filtered)
        start = (page - 1) * per_page
        end = start + per_page
        items = filtered[start:end]
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        result = {
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
        return api_response(data=result, message="Subscription plans retrieved")

    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Subscription plans retrieved")


@plans_bp.route("/<int:plan_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_plan(plan_id: int):
    """Retrieve details for a specific plan."""
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return api_error(code="PLAN_NOT_FOUND", message="Plan not found", status_code=404)

    current_user = getattr(g, "current_user", None)
    if current_user and current_user.role == ROLE_CUSTOMER and not plan.is_active:
        return api_error(code="PLAN_NOT_FOUND", message="Plan not found", status_code=404)

    return api_response(data=plan.to_dict(), message="Plan details retrieved")


@plans_bp.route("", methods=["POST"])
@staff_or_admin_required
def create_plan():
    """
    Create a new subscription plan with validation for billing intervals,
    pricing, minimum quantities, date ranges, and unique plan code.
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().upper()
    description = (data.get("description") or "").strip()
    billing_interval = (data.get("billing_interval") or "monthly").strip().lower()
    currency = (data.get("currency") or "USD").strip().upper()
    is_active = data.get("is_active", True)
    auto_renew = data.get("auto_renew", True)

    # 1. Required Name and Code
    if not name:
        return api_error(code="MISSING_NAME", message="Plan name is required", status_code=400)

    if not code:
        return api_error(code="MISSING_CODE", message="Plan code is required", status_code=400)

    # Code uniqueness check
    if Plan.query.filter_by(code=code).first():
        return api_error(
            code="DUPLICATE_PLAN_CODE",
            message=f"A subscription plan with code '{code}' already exists",
            status_code=409,
        )

    # 2. Billing Interval Validation
    if billing_interval not in VALID_INTERVALS:
        return api_error(
            code="INVALID_BILLING_INTERVAL",
            message=f"Billing frequency must be one of: {', '.join(VALID_INTERVALS)}",
            status_code=422,
        )

    try:
        billing_interval_count = int(data.get("billing_interval_count", 1))
        if billing_interval_count < 1:
            return api_error(code="INVALID_INTERVAL_COUNT", message="Interval count must be at least 1", status_code=422)
    except (ValueError, TypeError):
        return api_error(code="INVALID_INTERVAL_COUNT", message="Interval count must be a valid integer", status_code=422)

    # 3. Financials Validation
    base_price_dec, base_err = _parse_decimal(data.get("base_price"), "Base price")
    if base_err:
        return api_error(code="INVALID_PRICE", message=base_err, status_code=422)

    setup_fee_dec, setup_err = _parse_decimal(data.get("setup_fee", 0.00), "Setup fee")
    if setup_err:
        return api_error(code="INVALID_SETUP_FEE", message=setup_err, status_code=422)

    # 4. Trial days validation
    try:
        trial_days = int(data.get("trial_days", 0))
        if trial_days < 0:
            return api_error(code="INVALID_TRIAL_DAYS", message="Trial days cannot be negative", status_code=422)
    except (ValueError, TypeError):
        return api_error(code="INVALID_TRIAL_DAYS", message="Trial days must be a non-negative integer", status_code=422)

    # 5. Min Quantity validation
    try:
        min_quantity = int(data.get("min_quantity", 1))
        if min_quantity < 1:
            return api_error(code="INVALID_QUANTITY", message="Minimum subscription quantity must be at least 1", status_code=422)
    except (ValueError, TypeError):
        return api_error(code="INVALID_QUANTITY", message="Minimum subscription quantity must be a positive integer", status_code=422)

    # 6. Availability Date Range Validation
    av_from, from_err = _parse_date(data.get("available_from"), "available_from")
    if from_err:
        return api_error(code="INVALID_DATE_FORMAT", message=from_err, status_code=422)

    av_until, until_err = _parse_date(data.get("available_until"), "available_until")
    if until_err:
        return api_error(code="INVALID_DATE_FORMAT", message=until_err, status_code=422)

    if av_from and av_until and av_until < av_from:
        return api_error(
            code="INVALID_DATE_RANGE",
            message="available_until date cannot be earlier than available_from date",
            status_code=422,
        )

    # 7. Features and metadata
    raw_features = data.get("features") or []
    if isinstance(raw_features, str):
        features_list = [f.strip() for f in raw_features.split("\n") if f.strip()]
    elif isinstance(raw_features, list):
        features_list = [str(f).strip() for f in raw_features if str(f).strip()]
    else:
        features_list = []

    features_meta = {
        "bullets": features_list,
        "min_quantity": min_quantity,
        "available_from": av_from,
        "available_until": av_until,
        "auto_renew": bool(auto_renew),
    }

    plan = Plan(
        name=name,
        code=code,
        description=description if description else None,
        billing_interval=billing_interval,
        billing_interval_count=billing_interval_count,
        base_price=base_price_dec,
        setup_fee=setup_fee_dec,
        currency=currency,
        trial_days=trial_days,
        features=features_meta,
        is_active=bool(is_active),
    )
    db.session.add(plan)
    db.session.commit()

    _log_audit("PLAN_CREATED", "Plan", str(plan.id), new_values=plan.to_dict())

    return api_response(
        data=plan.to_dict(),
        message="Subscription plan created successfully",
        status_code=201,
    )


@plans_bp.route("/<int:plan_id>", methods=["PUT"])
@staff_or_admin_required
def update_plan(plan_id: int):
    """Update details of an existing subscription plan."""
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return api_error(code="PLAN_NOT_FOUND", message="Plan not found", status_code=404)

    data = request.get_json(silent=True) or {}
    old_values = plan.to_dict()

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return api_error(code="INVALID_NAME", message="Plan name cannot be empty", status_code=400)
        plan.name = name

    if "code" in data:
        code = (data.get("code") or "").strip().upper()
        if not code:
            return api_error(code="INVALID_CODE", message="Plan code cannot be empty", status_code=400)
        existing = Plan.query.filter_by(code=code).first()
        if existing and existing.id != plan.id:
            return api_error(
                code="DUPLICATE_PLAN_CODE",
                message=f"A subscription plan with code '{code}' already exists",
                status_code=409,
            )
        plan.code = code

    if "billing_interval" in data:
        billing_interval = (data.get("billing_interval") or "").strip().lower()
        if billing_interval not in VALID_INTERVALS:
            return api_error(
                code="INVALID_BILLING_INTERVAL",
                message=f"Billing frequency must be one of: {', '.join(VALID_INTERVALS)}",
                status_code=422,
            )
        plan.billing_interval = billing_interval

    if "billing_interval_count" in data:
        try:
            count = int(data["billing_interval_count"])
            if count < 1:
                return api_error(code="INVALID_INTERVAL_COUNT", message="Interval count must be at least 1", status_code=422)
            plan.billing_interval_count = count
        except (ValueError, TypeError):
            return api_error(code="INVALID_INTERVAL_COUNT", message="Interval count must be a valid integer", status_code=422)

    if "base_price" in data:
        base_price_dec, base_err = _parse_decimal(data.get("base_price"), "Base price")
        if base_err:
            return api_error(code="INVALID_PRICE", message=base_err, status_code=422)
        plan.base_price = base_price_dec

    if "setup_fee" in data:
        setup_fee_dec, setup_err = _parse_decimal(data.get("setup_fee", 0.00), "Setup fee")
        if setup_err:
            return api_error(code="INVALID_SETUP_FEE", message=setup_err, status_code=422)
        plan.setup_fee = setup_fee_dec

    if "currency" in data and data["currency"]:
        plan.currency = data["currency"].strip().upper()

    if "trial_days" in data:
        try:
            trial_days = int(data["trial_days"])
            if trial_days < 0:
                return api_error(code="INVALID_TRIAL_DAYS", message="Trial days cannot be negative", status_code=422)
            plan.trial_days = trial_days
        except (ValueError, TypeError):
            return api_error(code="INVALID_TRIAL_DAYS", message="Trial days must be a non-negative integer", status_code=422)

    if "description" in data:
        plan.description = data.get("description")

    if "is_active" in data:
        plan.is_active = bool(data["is_active"])

    # Extract current meta
    curr_dict = plan.to_dict()
    bullets = curr_dict.get("features", [])
    min_qty = curr_dict.get("min_quantity", 1)
    av_from = curr_dict.get("available_from")
    av_until = curr_dict.get("available_until")
    auto_renew = curr_dict.get("auto_renew", True)

    if "features" in data:
        raw_features = data["features"]
        if isinstance(raw_features, str):
            bullets = [f.strip() for f in raw_features.split("\n") if f.strip()]
        elif isinstance(raw_features, list):
            bullets = [str(f).strip() for f in raw_features if str(f).strip()]

    if "min_quantity" in data:
        try:
            min_qty = int(data["min_quantity"])
            if min_qty < 1:
                return api_error(code="INVALID_QUANTITY", message="Minimum subscription quantity must be at least 1", status_code=422)
        except (ValueError, TypeError):
            return api_error(code="INVALID_QUANTITY", message="Minimum quantity must be an integer", status_code=422)

    if "available_from" in data:
        av_from, from_err = _parse_date(data.get("available_from"), "available_from")
        if from_err:
            return api_error(code="INVALID_DATE_FORMAT", message=from_err, status_code=422)

    if "available_until" in data:
        av_until, until_err = _parse_date(data.get("available_until"), "available_until")
        if until_err:
            return api_error(code="INVALID_DATE_FORMAT", message=until_err, status_code=422)

    if av_from and av_until and av_until < av_from:
        return api_error(
            code="INVALID_DATE_RANGE",
            message="available_until date cannot be earlier than available_from date",
            status_code=422,
        )

    if "auto_renew" in data:
        auto_renew = bool(data["auto_renew"])

    plan.features = {
        "bullets": bullets,
        "min_quantity": min_qty,
        "available_from": av_from,
        "available_until": av_until,
        "auto_renew": auto_renew,
    }

    plan.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    _log_audit("PLAN_UPDATED", "Plan", str(plan.id), new_values=plan.to_dict(), old_values=old_values)

    return api_response(data=plan.to_dict(), message="Subscription plan updated successfully")


@plans_bp.route("/<int:plan_id>/status", methods=["PATCH"])
@staff_or_admin_required
def toggle_plan_status(plan_id: int):
    """Toggle plan active/inactive status."""
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return api_error(code="PLAN_NOT_FOUND", message="Plan not found", status_code=404)

    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        plan.is_active = bool(data["is_active"])
    else:
        plan.is_active = not plan.is_active

    plan.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    action_str = "activated" if plan.is_active else "deactivated"
    _log_audit(f"PLAN_{action_str.upper()}", "Plan", str(plan.id), new_values={"is_active": plan.is_active})

    return api_response(
        data=plan.to_dict(),
        message=f"Subscription plan {action_str} successfully",
    )


@plans_bp.route("/<int:plan_id>", methods=["DELETE"])
@staff_or_admin_required
def delete_plan(plan_id: int):
    """
    Delete a plan if it has no associated subscriptions or quotations.
    If associated, user is advised to deactivate it.
    """
    plan = db.session.get(Plan, plan_id)
    if not plan:
        return api_error(code="PLAN_NOT_FOUND", message="Plan not found", status_code=404)

    sub_count = Subscription.query.filter_by(plan_id=plan.id).count()
    quot_count = Quotation.query.filter_by(plan_id=plan.id).count()

    if sub_count > 0 or quot_count > 0:
        return api_error(
            code="PLAN_IN_USE",
            message="Cannot delete plan that is associated with active subscriptions or quotations. Please deactivate it instead.",
            details={"subscriptions": sub_count, "quotations": quot_count},
            status_code=409,
        )

    db.session.delete(plan)
    db.session.commit()

    _log_audit("PLAN_DELETED", "Plan", str(plan_id), old_values={"name": plan.name, "code": plan.code})

    return api_response(message="Subscription plan deleted successfully")
