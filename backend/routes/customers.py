from datetime import datetime, timezone
from decimal import Decimal
from flask import Blueprint, request, g
from sqlalchemy import or_
from backend.extensions import db
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.utils.response import api_response, api_error
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.validators import validate_email
from backend.utils.decorators import (
    role_required,
    staff_or_admin_required,
    admin_required,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_CUSTOMER,
)

customers_bp = Blueprint("customers", __name__, url_prefix="/customers")


def _get_customer_id_for_current_user() -> int | None:
    if not hasattr(g, "current_user") or not g.current_user:
        return None
    if g.current_user.role == ROLE_CUSTOMER:
        return g.current_user.customer_profile.id if g.current_user.customer_profile else -1
    return None


@customers_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_customers():
    """
    List customers with pagination, search, and active status filtering.
    Customers are isolated to their own record.
    """
    page, per_page = get_pagination_params()
    query = Customer.query

    cust_id_override = _get_customer_id_for_current_user()
    if cust_id_override is not None:
        query = query.filter(Customer.id == cust_id_override)
    else:
        status_filter = request.args.get("is_active")
        if status_filter is not None and status_filter != "":
            query = query.filter(Customer.is_active == (status_filter.lower() in ("true", "1")))

        search = request.args.get("search", "").strip()
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Customer.company_name.ilike(search_pattern),
                    Customer.contact_name.ilike(search_pattern),
                    Customer.email.ilike(search_pattern),
                )
            )

    query = query.order_by(Customer.company_name.asc())
    result = paginate_query(query, page, per_page)
    return api_response(data=result, message="Customers retrieved successfully")


@customers_bp.route("/<int:customer_id>", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_customer(customer_id: int):
    """Retrieve details for a single customer."""
    cust_id_override = _get_customer_id_for_current_user()
    if cust_id_override is not None and cust_id_override != customer_id:
        return api_error(code="FORBIDDEN", message="Access denied to this customer profile", status_code=403)

    customer = db.session.get(Customer, customer_id)
    if not customer:
        return api_error(code="NOT_FOUND", message="Customer not found", status_code=404)

    return api_response(data=customer.to_dict(), message="Customer retrieved successfully")


@customers_bp.route("", methods=["POST"])
@staff_or_admin_required
def create_customer():
    """Create a new customer profile (Staff and Admin)."""
    data = request.get_json(silent=True) or {}
    company_name = (data.get("company_name") or "").strip()
    contact_name = (data.get("contact_name") or company_name).strip()
    email = (data.get("email") or "").strip().lower()

    if not company_name and not contact_name:
        return api_error(code="MISSING_FIELD", message="Company name or contact name is required", status_code=422)

    if not email or not validate_email(email):
        return api_error(code="INVALID_EMAIL", message="A valid email is required", status_code=422)

    # Check for duplicate email under customer
    existing = Customer.query.filter_by(email=email).first()
    if existing:
        return api_error(code="CONFLICT", message=f"Customer with email '{email}' already exists", status_code=409)

    customer = Customer(
        company_name=company_name or contact_name,
        contact_name=contact_name or company_name,
        email=email,
        phone=(data.get("phone") or "").strip() or None,
        billing_street=(data.get("billing_street") or "").strip() or None,
        billing_city=(data.get("billing_city") or "").strip() or None,
        billing_state=(data.get("billing_state") or "").strip() or None,
        billing_postal_code=(data.get("billing_postal_code") or "").strip() or None,
        billing_country=(data.get("billing_country") or "United States").strip(),
        currency=(data.get("currency") or "USD").strip().upper(),
        payment_terms_days=int(data.get("payment_terms_days", 30)),
        credit_limit=Decimal(str(data.get("credit_limit", 0.00))),
        notes=(data.get("notes") or "").strip() or None,
        is_active=bool(data.get("is_active", True)),
    )

    db.session.add(customer)
    db.session.flush()

    # Audit log
    current_user = getattr(g, "current_user", None)
    audit = AuditLog(
        user_id=current_user.id if current_user else None,
        action="CUSTOMER_CREATED",
        entity_type="Customer",
        entity_id=str(customer.id),
        new_values={"company_name": customer.company_name, "email": customer.email},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None,
    )
    db.session.add(audit)
    db.session.commit()

    return api_response(data=customer.to_dict(), message="Customer created successfully", status_code=201)


@customers_bp.route("/<int:customer_id>", methods=["PUT"])
@staff_or_admin_required
def update_customer(customer_id: int):
    """Update customer profile information."""
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return api_error(code="NOT_FOUND", message="Customer not found", status_code=404)

    data = request.get_json(silent=True) or {}
    old_values = customer.to_dict()

    if "company_name" in data:
        val = (data.get("company_name") or "").strip()
        if val:
            customer.company_name = val
    if "contact_name" in data:
        val = (data.get("contact_name") or "").strip()
        if val:
            customer.contact_name = val
    if "email" in data:
        email = (data.get("email") or "").strip().lower()
        if not validate_email(email):
            return api_error(code="INVALID_EMAIL", message="A valid email is required", status_code=422)
        # Check uniqueness if changed
        if email != customer.email:
            existing = Customer.query.filter_by(email=email).first()
            if existing:
                return api_error(code="CONFLICT", message=f"Customer with email '{email}' already exists", status_code=409)
            customer.email = email
    if "phone" in data:
        customer.phone = (data.get("phone") or "").strip() or None
    if "billing_street" in data:
        customer.billing_street = (data.get("billing_street") or "").strip() or None
    if "billing_city" in data:
        customer.billing_city = (data.get("billing_city") or "").strip() or None
    if "billing_state" in data:
        customer.billing_state = (data.get("billing_state") or "").strip() or None
    if "billing_postal_code" in data:
        customer.billing_postal_code = (data.get("billing_postal_code") or "").strip() or None
    if "billing_country" in data:
        customer.billing_country = (data.get("billing_country") or "United States").strip()
    if "currency" in data:
        customer.currency = (data.get("currency") or "USD").strip().upper()
    if "payment_terms_days" in data:
        try:
            customer.payment_terms_days = int(data["payment_terms_days"])
        except (ValueError, TypeError):
            pass
    if "credit_limit" in data:
        try:
            customer.credit_limit = Decimal(str(data["credit_limit"]))
        except Exception:
            pass
    if "notes" in data:
        customer.notes = (data.get("notes") or "").strip() or None
    if "is_active" in data:
        customer.is_active = bool(data["is_active"])

    current_user = getattr(g, "current_user", None)
    audit = AuditLog(
        user_id=current_user.id if current_user else None,
        action="CUSTOMER_UPDATED",
        entity_type="Customer",
        entity_id=str(customer.id),
        old_values=old_values,
        new_values=customer.to_dict(),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None,
    )
    db.session.add(audit)
    db.session.commit()

    return api_response(data=customer.to_dict(), message="Customer updated successfully")


@customers_bp.route("/<int:customer_id>", methods=["DELETE"])
@admin_required
def delete_customer(customer_id: int):
    """Deactivate or delete customer (Admin only)."""
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return api_error(code="NOT_FOUND", message="Customer not found", status_code=404)

    # If customer has active subscriptions or invoices, deactivate rather than hard delete
    has_active_subs = any(s.status == "active" for s in customer.subscriptions)
    if has_active_subs or customer.invoices:
        customer.is_active = False
        db.session.commit()
        return api_response(data=customer.to_dict(), message="Customer has active records; account has been deactivated.")

    db.session.delete(customer)
    db.session.commit()
    return api_response(message="Customer deleted successfully")
