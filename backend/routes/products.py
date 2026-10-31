from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, g
from backend.extensions import db
from backend.models.product import Product, ProductVariant
from backend.models.audit_log import AuditLog
from backend.models.quotation import QuotationLine
from backend.models.subscription import SubscriptionLine
from backend.models.invoice import InvoiceLine
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import (
    role_required,
    staff_or_admin_required,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_CUSTOMER,
)

products_bp = Blueprint("products", __name__, url_prefix="/products")


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


# ============================================================================
# Product Catalog Routes
# ============================================================================

@products_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_products():
    """
    List products with pagination, search, recurring filter, and status filter.
    Customers are restricted to active products only.
    """
    page, per_page = get_pagination_params()
    query = Product.query

    # RBAC: Customers can only see active products
    current_user = getattr(g, "current_user", None)
    if current_user and current_user.role == ROLE_CUSTOMER:
        query = query.filter(Product.is_active.is_(True))
    else:
        status_filter = request.args.get("is_active")
        if status_filter is not None:
            query = query.filter(Product.is_active == (status_filter.lower() in ("true", "1")))

    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))

    recurring_only = request.args.get("is_recurring")
    if recurring_only is not None:
        query = query.filter(Product.is_recurring == (recurring_only.lower() in ("true", "1")))

    query = query.order_by(Product.created_at.desc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Products retrieved successfully")


@products_bp.route("/<int:product_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_product(product_id: int):
    """Retrieve details for a single product."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    current_user = getattr(g, "current_user", None)
    if current_user and current_user.role == ROLE_CUSTOMER and not product.is_active:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    return api_response(data=product.to_dict(), message="Product retrieved successfully")


@products_bp.route("", methods=["POST"])
@staff_or_admin_required
def create_product():
    """
    Create a new product with validation for required fields, price, and unique SKU.
    Optionally accepts initial variants.
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    sku = (data.get("sku") or "").strip().upper()
    description = (data.get("description") or "").strip()
    currency = (data.get("currency") or "USD").strip().upper()
    unit_of_measure = (data.get("unit_of_measure") or "unit").strip().lower()
    is_recurring = data.get("is_recurring", True)
    is_active = data.get("is_active", True)

    # Validations
    if not name:
        return api_error(code="MISSING_NAME", message="Product name is required", status_code=400)

    if not sku:
        return api_error(code="MISSING_SKU", message="Product SKU is required", status_code=400)

    # SKU uniqueness check
    if Product.query.filter_by(sku=sku).first():
        return api_error(
            code="DUPLICATE_SKU",
            message=f"Product with SKU '{sku}' already exists",
            status_code=409,
        )

    # Base price validation
    default_price_dec, price_err = _parse_decimal(data.get("default_price"), "Base price")
    if price_err:
        return api_error(code="INVALID_PRICE", message=price_err, status_code=422)

    product = Product(
        name=name,
        sku=sku,
        description=description if description else None,
        default_price=default_price_dec,
        currency=currency,
        unit_of_measure=unit_of_measure,
        is_recurring=bool(is_recurring),
        is_active=bool(is_active),
    )
    db.session.add(product)
    db.session.flush()

    # Optional initial variants
    variants_input = data.get("variants") or []
    if isinstance(variants_input, list):
        for v in variants_input:
            if not isinstance(v, dict):
                continue
            v_name = (v.get("name") or "").strip()
            v_sku = (v.get("sku") or "").strip().upper()
            if not v_name or not v_sku:
                continue

            # Variant SKU collision check
            if ProductVariant.query.filter_by(sku=v_sku).first():
                db.session.rollback()
                return api_error(
                    code="DUPLICATE_VARIANT_SKU",
                    message=f"Variant with SKU '{v_sku}' already exists",
                    status_code=409,
                )

            v_price_extra, v_price_err = _parse_decimal(v.get("price_extra", 0), "Variant additional price")
            if v_price_err:
                db.session.rollback()
                return api_error(code="INVALID_PRICE", message=v_price_err, status_code=422)

            v_attrs = v.get("attributes") or {}
            if "description" not in v_attrs and v.get("description"):
                v_attrs["description"] = v.get("description").strip()

            variant = ProductVariant(
                product_id=product.id,
                name=v_name,
                sku=v_sku,
                price_extra=v_price_extra,
                attributes=v_attrs,
                is_active=bool(v.get("is_active", True)),
            )
            db.session.add(variant)

    db.session.commit()
    _log_audit("PRODUCT_CREATED", "Product", str(product.id), new_values=product.to_dict())

    return api_response(
        data=product.to_dict(),
        message="Product created successfully",
        status_code=201,
    )


@products_bp.route("/<int:product_id>", methods=["PUT"])
@staff_or_admin_required
def update_product(product_id: int):
    """Update an existing product's details."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    data = request.get_json(silent=True) or {}
    old_values = product.to_dict()

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return api_error(code="INVALID_NAME", message="Product name cannot be empty", status_code=400)
        product.name = name

    if "sku" in data:
        sku = (data.get("sku") or "").strip().upper()
        if not sku:
            return api_error(code="INVALID_SKU", message="Product SKU cannot be empty", status_code=400)
        existing = Product.query.filter_by(sku=sku).first()
        if existing and existing.id != product.id:
            return api_error(
                code="DUPLICATE_SKU",
                message=f"Product with SKU '{sku}' already exists",
                status_code=409,
            )
        product.sku = sku

    if "default_price" in data:
        default_price_dec, price_err = _parse_decimal(data.get("default_price"), "Base price")
        if price_err:
            return api_error(code="INVALID_PRICE", message=price_err, status_code=422)
        product.default_price = default_price_dec

    if "description" in data:
        product.description = data.get("description")
    if "currency" in data and data["currency"]:
        product.currency = data["currency"].strip().upper()
    if "unit_of_measure" in data and data["unit_of_measure"]:
        product.unit_of_measure = data["unit_of_measure"].strip().lower()
    if "is_recurring" in data:
        product.is_recurring = bool(data["is_recurring"])
    if "is_active" in data:
        product.is_active = bool(data["is_active"])

    product.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    _log_audit("PRODUCT_UPDATED", "Product", str(product.id), new_values=product.to_dict(), old_values=old_values)

    return api_response(data=product.to_dict(), message="Product updated successfully")


@products_bp.route("/<int:product_id>/status", methods=["PATCH"])
@staff_or_admin_required
def toggle_product_status(product_id: int):
    """Activate or deactivate a product."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        product.is_active = bool(data["is_active"])
    else:
        product.is_active = not product.is_active

    product.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    action_str = "activated" if product.is_active else "deactivated"
    _log_audit(f"PRODUCT_{action_str.upper()}", "Product", str(product.id), new_values={"is_active": product.is_active})

    return api_response(
        data=product.to_dict(),
        message=f"Product {action_str} successfully",
    )


@products_bp.route("/<int:product_id>", methods=["DELETE"])
@staff_or_admin_required
def delete_product(product_id: int):
    """
    Delete a product if it has no associated quotation, subscription, or invoice lines.
    If associated, user is advised to deactivate it.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    # Check for linked records
    q_count = QuotationLine.query.filter_by(product_id=product.id).count()
    s_count = SubscriptionLine.query.filter_by(product_id=product.id).count()
    i_count = InvoiceLine.query.filter_by(product_id=product.id).count()

    if q_count > 0 or s_count > 0 or i_count > 0:
        return api_error(
            code="PRODUCT_IN_USE",
            message="Cannot delete product that is referenced by active quotations, subscriptions, or invoices. Please deactivate it instead.",
            details={
                "quotation_lines": q_count,
                "subscription_lines": s_count,
                "invoice_lines": i_count,
            },
            status_code=409,
        )

    db.session.delete(product)
    db.session.commit()
    _log_audit("PRODUCT_DELETED", "Product", str(product_id), old_values={"name": product.name, "sku": product.sku})

    return api_response(message="Product deleted successfully")


# ============================================================================
# Product Variant Routes
# ============================================================================

@products_bp.route("/<int:product_id>/variants", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_variants(product_id: int):
    """List all variants for a specific product."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    query = ProductVariant.query.filter_by(product_id=product_id)

    current_user = getattr(g, "current_user", None)
    if current_user and current_user.role == ROLE_CUSTOMER:
        query = query.filter_by(is_active=True)
    else:
        status_filter = request.args.get("is_active")
        if status_filter is not None:
            query = query.filter_by(is_active=(status_filter.lower() in ("true", "1")))

    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(ProductVariant.name.ilike(f"%{search}%") | ProductVariant.sku.ilike(f"%{search}%"))

    variants = query.order_by(ProductVariant.created_at.asc()).all()
    return api_response(
        data={
            "product_id": product.id,
            "product_name": product.name,
            "base_price": float(product.default_price),
            "currency": product.currency,
            "items": [v.to_dict() for v in variants],
            "total_items": len(variants),
        },
        message="Product variants retrieved successfully",
    )


@products_bp.route("/<int:product_id>/variants", methods=["POST"])
@staff_or_admin_required
def create_variant(product_id: int):
    """
    Create a configurable variant for a product.
    Calculates final price = base_price + price_extra.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return api_error(code="PRODUCT_NOT_FOUND", message="Product not found", status_code=404)

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    sku = (data.get("sku") or "").strip().upper()
    description = (data.get("description") or "").strip()
    is_active = data.get("is_active", True)

    if not name:
        return api_error(code="MISSING_NAME", message="Variant name is required", status_code=400)

    if not sku:
        return api_error(code="MISSING_SKU", message="Variant SKU is required", status_code=400)

    # Variant SKU uniqueness check
    if ProductVariant.query.filter_by(sku=sku).first():
        return api_error(
            code="DUPLICATE_SKU",
            message=f"Product variant with SKU '{sku}' already exists",
            status_code=409,
        )

    price_extra_dec, price_err = _parse_decimal(data.get("price_extra", 0), "Additional price")
    if price_err:
        return api_error(code="INVALID_PRICE", message=price_err, status_code=422)

    attributes = data.get("attributes") or {}
    if not isinstance(attributes, dict):
        attributes = {}
    if description:
        attributes["description"] = description

    variant = ProductVariant(
        product_id=product.id,
        name=name,
        sku=sku,
        price_extra=price_extra_dec,
        attributes=attributes,
        is_active=bool(is_active),
    )
    db.session.add(variant)
    db.session.commit()

    _log_audit("VARIANT_CREATED", "ProductVariant", str(variant.id), new_values=variant.to_dict())

    return api_response(
        data=variant.to_dict(),
        message="Product variant created successfully",
        status_code=201,
    )


@products_bp.route("/<int:product_id>/variants/<int:variant_id>", methods=["GET"])
@products_bp.route("/variants/<int:variant_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_variant(variant_id: int, product_id: int = None):
    """Retrieve details for a single product variant."""
    variant = db.session.get(ProductVariant, variant_id)
    if not variant:
        return api_error(code="VARIANT_NOT_FOUND", message="Variant not found", status_code=404)

    if product_id is not None and variant.product_id != product_id:
        return api_error(code="VARIANT_MISMATCH", message="Variant does not belong to specified product", status_code=400)

    current_user = getattr(g, "current_user", None)
    if current_user and current_user.role == ROLE_CUSTOMER and not variant.is_active:
        return api_error(code="VARIANT_NOT_FOUND", message="Variant not found", status_code=404)

    return api_response(data=variant.to_dict(), message="Product variant retrieved successfully")


@products_bp.route("/<int:product_id>/variants/<int:variant_id>", methods=["PUT"])
@products_bp.route("/variants/<int:variant_id>", methods=["PUT"])
@staff_or_admin_required
def update_variant(variant_id: int, product_id: int = None):
    """Update details of a product variant."""
    variant = db.session.get(ProductVariant, variant_id)
    if not variant:
        return api_error(code="VARIANT_NOT_FOUND", message="Variant not found", status_code=404)

    if product_id is not None and variant.product_id != product_id:
        return api_error(code="VARIANT_MISMATCH", message="Variant does not belong to specified product", status_code=400)

    data = request.get_json(silent=True) or {}
    old_values = variant.to_dict()

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return api_error(code="INVALID_NAME", message="Variant name cannot be empty", status_code=400)
        variant.name = name

    if "sku" in data:
        sku = (data.get("sku") or "").strip().upper()
        if not sku:
            return api_error(code="INVALID_SKU", message="Variant SKU cannot be empty", status_code=400)
        existing = ProductVariant.query.filter_by(sku=sku).first()
        if existing and existing.id != variant.id:
            return api_error(
                code="DUPLICATE_SKU",
                message=f"Product variant with SKU '{sku}' already exists",
                status_code=409,
            )
        variant.sku = sku

    if "price_extra" in data:
        price_extra_dec, price_err = _parse_decimal(data.get("price_extra"), "Additional price")
        if price_err:
            return api_error(code="INVALID_PRICE", message=price_err, status_code=422)
        variant.price_extra = price_extra_dec

    attrs = dict(variant.attributes or {})
    if "description" in data:
        attrs["description"] = (data.get("description") or "").strip()
    if "attributes" in data and isinstance(data["attributes"], dict):
        attrs.update(data["attributes"])
    variant.attributes = attrs

    if "is_active" in data:
        variant.is_active = bool(data["is_active"])

    db.session.commit()
    _log_audit("VARIANT_UPDATED", "ProductVariant", str(variant.id), new_values=variant.to_dict(), old_values=old_values)

    return api_response(data=variant.to_dict(), message="Product variant updated successfully")


@products_bp.route("/<int:product_id>/variants/<int:variant_id>/status", methods=["PATCH"])
@products_bp.route("/variants/<int:variant_id>/status", methods=["PATCH"])
@staff_or_admin_required
def toggle_variant_status(variant_id: int, product_id: int = None):
    """Toggle variant active/inactive status."""
    variant = db.session.get(ProductVariant, variant_id)
    if not variant:
        return api_error(code="VARIANT_NOT_FOUND", message="Variant not found", status_code=404)

    if product_id is not None and variant.product_id != product_id:
        return api_error(code="VARIANT_MISMATCH", message="Variant does not belong to specified product", status_code=400)

    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        variant.is_active = bool(data["is_active"])
    else:
        variant.is_active = not variant.is_active

    db.session.commit()
    action_str = "activated" if variant.is_active else "deactivated"
    _log_audit(f"VARIANT_{action_str.upper()}", "ProductVariant", str(variant.id), new_values={"is_active": variant.is_active})

    return api_response(
        data=variant.to_dict(),
        message=f"Product variant {action_str} successfully",
    )


@products_bp.route("/<int:product_id>/variants/<int:variant_id>", methods=["DELETE"])
@products_bp.route("/variants/<int:variant_id>", methods=["DELETE"])
@staff_or_admin_required
def delete_variant(variant_id: int, product_id: int = None):
    """
    Delete a variant if not referenced by quotation or subscription lines.
    """
    variant = db.session.get(ProductVariant, variant_id)
    if not variant:
        return api_error(code="VARIANT_NOT_FOUND", message="Variant not found", status_code=404)

    if product_id is not None and variant.product_id != product_id:
        return api_error(code="VARIANT_MISMATCH", message="Variant does not belong to specified product", status_code=400)

    q_count = QuotationLine.query.filter_by(product_variant_id=variant.id).count()
    s_count = SubscriptionLine.query.filter_by(product_variant_id=variant.id).count()

    if q_count > 0 or s_count > 0:
        return api_error(
            code="VARIANT_IN_USE",
            message="Cannot delete variant that is referenced by active quotations or subscriptions. Please deactivate it instead.",
            details={
                "quotation_lines": q_count,
                "subscription_lines": s_count,
            },
            status_code=409,
        )

    db.session.delete(variant)
    db.session.commit()
    _log_audit("VARIANT_DELETED", "ProductVariant", str(variant_id), old_values={"name": variant.name, "sku": variant.sku})

    return api_response(message="Product variant deleted successfully")
