from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from backend.extensions import db
from backend.models.user import User
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.utils.response import api_response, api_error
from backend.utils.validators import validate_password, validate_email
from backend.utils.decorators import role_required, admin_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Public registration endpoint.
    Creates a new user account. Defaults to 'customer' role.
    If no users exist in the database, automatically bootstraps the first user as 'admin'.
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    company_name = (data.get("company_name") or "").strip()

    # Validation
    if not email or not validate_email(email):
        return api_error(
            code="INVALID_EMAIL",
            message="A valid email address is required",
            status_code=400
        )

    if not first_name or not last_name:
        return api_error(
            code="MISSING_NAME",
            message="First name and last name are required",
            status_code=400
        )

    # Password complexity check (more than 8 chars, uppercase, lowercase, special char)
    is_valid_pwd, pwd_errors = validate_password(password)
    if not is_valid_pwd:
        return api_error(
            code="INVALID_PASSWORD",
            message="Password does not meet security requirements",
            details=pwd_errors,
            status_code=422
        )

    # Check for existing user
    if User.query.filter_by(email=email).first():
        return api_error(
            code="EMAIL_ALREADY_EXISTS",
            message="An account with this email address already exists",
            status_code=409
        )

    # If first user in system, bootstrap as admin; otherwise customer
    is_first_user = User.query.count() == 0
    role = ROLE_ADMIN if is_first_user else ROLE_CUSTOMER

    new_user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=True
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.flush()

    # If customer role, also create corresponding Customer profile
    customer_record = None
    if role == ROLE_CUSTOMER:
        customer_record = Customer(
            user_id=new_user.id,
            company_name=company_name or f"{first_name} {last_name}".strip(),
            contact_name=f"{first_name} {last_name}".strip(),
            email=email,
            currency="USD",
            payment_terms_days=30
        )
        db.session.add(customer_record)

    # Audit log
    audit = AuditLog(
        user_id=new_user.id,
        action="USER_REGISTERED",
        entity_type="User",
        entity_id=str(new_user.id),
        new_values={"email": email, "role": role},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    db.session.add(audit)
    db.session.commit()

    # Generate JWT tokens
    # Using string ID for JWT subject to be JSON-serializable
    access_token = create_access_token(identity=str(new_user.id), additional_claims={"role": new_user.role})
    refresh_token = create_refresh_token(identity=str(new_user.id))

    return api_response(
        data={
            "user": new_user.to_dict(),
            "customer": customer_record.to_dict() if customer_record else None,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        },
        message="Registration successful",
        status_code=201
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user with email and password, returning JWT tokens.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return api_error(
            code="MISSING_CREDENTIALS",
            message="Both email and password are required",
            status_code=400
        )

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return api_error(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
            status_code=401
        )

    if not user.is_active:
        return api_error(
            code="ACCOUNT_DISABLED",
            message="Your account has been deactivated. Please contact an administrator.",
            status_code=403
        )

    # Create tokens
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    refresh_token = create_refresh_token(identity=str(user.id))

    # Record login audit
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="User",
        entity_id=str(user.id),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    db.session.add(audit)
    db.session.commit()

    return api_response(
        data={
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        },
        message="Login successful"
    )


@auth_bp.route("/me", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def get_current_user():
    """
    Get profile information of the currently authenticated user.
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return api_error(code="USER_NOT_FOUND", message="User not found", status_code=404)

    user_data = user.to_dict()
    if user.customer_profile:
        user_data["customer"] = user.customer_profile.to_dict()

    return api_response(data=user_data, message="Current user profile")


@auth_bp.route("/create-staff", methods=["POST"])
@admin_required
def create_staff():
    """
    Admin-only endpoint: Create a Staff account.
    Non-admin users receive a 403 Forbidden.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()

    if not email or not validate_email(email):
        return api_error(code="INVALID_EMAIL", message="A valid email is required", status_code=400)

    if not first_name or not last_name:
        return api_error(code="MISSING_NAME", message="First name and last name are required", status_code=400)

    is_valid_pwd, pwd_errors = validate_password(password)
    if not is_valid_pwd:
        return api_error(
            code="INVALID_PASSWORD",
            message="Password does not meet security requirements",
            details=pwd_errors,
            status_code=422
        )

    if User.query.filter_by(email=email).first():
        return api_error(code="EMAIL_EXISTS", message="User with this email already exists", status_code=409)

    staff_user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=ROLE_STAFF,
        is_active=True
    )
    staff_user.set_password(password)
    db.session.add(staff_user)
    db.session.flush()

    # Audit log
    admin_id = int(get_jwt_identity())
    audit = AuditLog(
        user_id=admin_id,
        action="STAFF_ACCOUNT_CREATED",
        entity_type="User",
        entity_id=str(staff_user.id),
        new_values={"email": email, "role": ROLE_STAFF},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None
    )
    db.session.add(audit)
    db.session.commit()

    return api_response(
        data=staff_user.to_dict(),
        message="Staff account successfully created",
        status_code=201
    )


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh_token():
    """
    Generate a new access token using a valid refresh token.
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return api_error(code="UNAUTHORIZED", message="User inactive or removed", status_code=401)

    new_access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return api_response(
        data={"access_token": new_access_token, "token_type": "Bearer"},
        message="Access token refreshed"
    )
