from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, g
from sqlalchemy import or_
from backend.extensions import db
from backend.models.discount import DiscountRule
from backend.models.audit_log import AuditLog
from backend.services.discount_service import DiscountService
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

discounts_bp = Blueprint("discounts", __name__, url_prefix="/discounts")


@discounts_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_discounts():
    """
    List discount rules and promotional coupons.
    Supports filtering by active status, search by code/name, and pagination.
    """
    page, per_page = get_pagination_params()
    query = DiscountRule.query

    active_only = request.args.get("is_active")
    if active_only is not None and active_only != "":
        query = query.filter_by(is_active=(active_only.lower() in ("true", "1")))

    search = request.args.get("search", "").strip()
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                DiscountRule.code.ilike(search_pattern),
                DiscountRule.name.ilike(search_pattern)
            )
        )

    discount_type = request.args.get("discount_type")
    if discount_type and discount_type.lower() != "all":
        query = query.filter_by(discount_type=discount_type.lower())

    query = query.order_by(DiscountRule.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Discount rules retrieved")


@discounts_bp.route("/<int:discount_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_discount(discount_id: int):
    """Retrieve discount rule details."""
    rule = DiscountRule.query.get_or_404(discount_id)
    return api_response(data=rule.to_dict(), message="Discount rule retrieved")


@discounts_bp.route("", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def create_discount():
    """
    Create a new promotional discount / coupon rule.
    """
    data = request.get_json(silent=True) or {}

    raw_code = data.get("code")
    if not raw_code or not str(raw_code).strip():
        return api_error(code="VALIDATION_ERROR", message="Coupon code is required", status_code=422)

    code = str(raw_code).strip().upper()
    existing = DiscountRule.query.filter_by(code=code).first()
    if existing:
        return api_error(code="CONFLICT", message=f"Coupon code '{code}' already exists", status_code=409)

    name = (data.get("name") or "").strip()
    if not name:
        return api_error(code="VALIDATION_ERROR", message="Promotion campaign name is required", status_code=422)

    disc_type = (data.get("discount_type") or "percentage").lower().strip()
    if disc_type not in ("percentage", "fixed"):
        return api_error(code="VALIDATION_ERROR", message="discount_type must be 'percentage' or 'fixed'", status_code=422)

    try:
        val = Decimal(str(data.get("value", 0)))
        if val <= Decimal("0.00"):
            return api_error(code="VALIDATION_ERROR", message="Discount value must be greater than zero", status_code=422)
        if disc_type == "percentage" and val > Decimal("100.00"):
            return api_error(code="VALIDATION_ERROR", message="Percentage discount cannot exceed 100%", status_code=422)
    except Exception:
        return api_error(code="VALIDATION_ERROR", message="Invalid discount value", status_code=422)

    min_order = Decimal(str(data.get("min_order_amount", 0)))
    max_discount = Decimal(str(data["max_discount_amount"])) if data.get("max_discount_amount") is not None else None

    # Validity dates
    valid_from = None
    if data.get("valid_from"):
        try:
            valid_from = datetime.fromisoformat(data["valid_from"])
            if not valid_from.tzinfo:
                valid_from = valid_from.replace(tzinfo=timezone.utc)
        except Exception:
            return api_error(code="INVALID_DATE", message="Invalid valid_from timestamp", status_code=422)

    valid_to = None
    if data.get("valid_to"):
        try:
            valid_to = datetime.fromisoformat(data["valid_to"])
            if not valid_to.tzinfo:
                valid_to = valid_to.replace(tzinfo=timezone.utc)
        except Exception:
            return api_error(code="INVALID_DATE", message="Invalid valid_to timestamp", status_code=422)

    if valid_from and valid_to and valid_to < valid_from:
        return api_error(code="INVALID_DATE_RANGE", message="valid_to date cannot be earlier than valid_from date", status_code=422)

    max_uses = int(data["max_uses"]) if data.get("max_uses") is not None and str(data["max_uses"]).isdigit() else None
    applicable_plans = data.get("applicable_plans") if isinstance(data.get("applicable_plans"), list) else []

    rule = DiscountRule(
        code=code,
        name=name,
        description=data.get("description"),
        discount_type=disc_type,
        value=val,
        min_order_amount=min_order,
        max_discount_amount=max_discount,
        valid_from=valid_from,
        valid_to=valid_to,
        max_uses=max_uses,
        current_uses=0,
        is_active=bool(data.get("is_active", True)),
        applicable_plans=applicable_plans
    )
    db.session.add(rule)
    db.session.flush()

    audit = AuditLog(
        user_id=g.current_user.id,
        action="DISCOUNT_CREATED",
        entity_type="DiscountRule",
        entity_id=str(rule.id),
        new_values={"code": rule.code, "value": float(rule.value), "discount_type": rule.discount_type}
    )
    db.session.add(audit)
    db.session.commit()

    return api_response(data=rule.to_dict(), message="Discount rule created successfully", status_code=201)


@discounts_bp.route("/<int:discount_id>", methods=["PUT"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def update_discount(discount_id: int):
    """
    Update configuration of an existing discount rule.
    """
    rule = DiscountRule.query.get_or_404(discount_id)
    data = request.get_json(silent=True) or {}

    if "name" in data:
        rule.name = str(data["name"]).strip()
    if "description" in data:
        rule.description = data["description"]
    if "is_active" in data:
        rule.is_active = bool(data["is_active"])
    if "max_uses" in data:
        rule.max_uses = int(data["max_uses"]) if data["max_uses"] is not None else None
    if "min_order_amount" in data:
        rule.min_order_amount = Decimal(str(data["min_order_amount"]))
    if "max_discount_amount" in data:
        rule.max_discount_amount = Decimal(str(data["max_discount_amount"])) if data["max_discount_amount"] is not None else None
    if "applicable_plans" in data and isinstance(data["applicable_plans"], list):
        rule.applicable_plans = data["applicable_plans"]

    db.session.commit()
    return api_response(data=rule.to_dict(), message="Discount rule updated successfully")


@discounts_bp.route("/<int:discount_id>/toggle-status", methods=["POST"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def toggle_discount_status(discount_id: int):
    """Toggle active/inactive status of a discount rule."""
    rule = DiscountRule.query.get_or_404(discount_id)
    rule.is_active = not rule.is_active
    db.session.commit()
    status_label = "activated" if rule.is_active else "deactivated"
    return api_response(data=rule.to_dict(), message=f"Discount rule {rule.code} {status_label}")


@discounts_bp.route("/validate/<code>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def validate_coupon_code(code: str):
    """
    Validates a specific coupon code with optional order amount and plan qualifiers.
    Query params: ?amount=100.00&plan_code=PLAN-STARTER-MO
    """
    amount = request.args.get("amount", type=float, default=0.0)
    plan_code = request.args.get("plan_code")

    is_valid, discount_amount, rule, err_msg = DiscountService.validate_and_calculate_discount(
        code=code,
        eligible_amount=amount,
        plan_code=plan_code
    )

    if not is_valid:
        return api_error(
            code="COUPON_INVALID",
            message=err_msg or "Coupon is invalid or cannot be applied",
            details={"rule": rule.to_dict() if rule else None},
            status_code=400
        )

    payload = {
        **rule.to_dict(),
        "calculated_discount": float(discount_amount),
        "eligible_order_amount": float(amount)
    }
    return api_response(data=payload, message=f"Coupon '{rule.code}' is valid")
