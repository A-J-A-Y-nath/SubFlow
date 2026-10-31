from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.extensions import db
from backend.utils.response import api_error

ROLE_ADMIN = "admin"
ROLE_STAFF = "staff"
ROLE_CUSTOMER = "customer"
ALL_ROLES = (ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)


def role_required(*allowed_roles):
    """
    Decorator that verifies:
    1. A valid JWT token is present in the request.
    2. The authenticated user exists and is active.
    3. The user's role is included in allowed_roles.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify JWT presence and validity
            try:
                verify_jwt_in_request()
            except Exception as e:
                return api_error(
                    code="UNAUTHORIZED",
                    message="Missing or invalid authentication token",
                    details=str(e),
                    status_code=401
                )

            user_id = get_jwt_identity()
            # Lazy import to avoid circular dependencies with models
            from backend.models.user import User

            user = db.session.get(User, int(user_id))
            if not user:
                return api_error(
                    code="USER_NOT_FOUND",
                    message="User account associated with this token was not found",
                    status_code=401
                )

            if not user.is_active:
                return api_error(
                    code="ACCOUNT_DISABLED",
                    message="Your account has been deactivated. Please contact support.",
                    status_code=403
                )

            if allowed_roles and user.role not in allowed_roles:
                return api_error(
                    code="FORBIDDEN",
                    message=f"Access denied. Requires one of the following roles: {', '.join(allowed_roles)}",
                    details={"user_role": user.role, "required_roles": list(allowed_roles)},
                    status_code=403
                )

            # Store current_user in Flask's g object for easy access in route handlers
            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper
    return decorator


def admin_required(fn):
    """Convenience decorator requiring Admin role."""
    return role_required(ROLE_ADMIN)(fn)


def staff_or_admin_required(fn):
    """Convenience decorator requiring Staff or Admin role."""
    return role_required(ROLE_ADMIN, ROLE_STAFF)(fn)
