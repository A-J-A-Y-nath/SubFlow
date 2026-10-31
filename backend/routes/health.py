from datetime import datetime, timezone
from flask import Blueprint, current_app
from sqlalchemy import text
from backend.extensions import db
from backend.utils.response import api_response, api_error

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    System and database health check endpoint.
    Verifies that the database is accessible.
    """
    db_status = False
    db_error = None

    try:
        # Execute simple query to test DB connectivity
        db.session.execute(text("SELECT 1"))
        db_status = True
    except Exception as e:
        db_error = str(e)

    payload = {
        "status": "healthy" if db_status else "degraded",
        "service": "SubFlow API",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_connected": db_status,
        "environment": current_app.config.get("ENV", "development"),
    }

    if not db_status:
        payload["database_error"] = db_error
        return api_error(
            code="SERVICE_DEGRADED",
            message="Database connection check failed",
            details=payload,
            status_code=503
        )

    return api_response(data=payload, message="SubFlow API is healthy")
