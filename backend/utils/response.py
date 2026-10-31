from typing import Any, Optional
from flask import jsonify, Response


def api_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[dict] = None
) -> tuple[Response, int]:
    """
    Standard successful JSON response envelope for SubFlow APIs.
    """
    payload = {
        "success": True,
        "message": message,
        "data": data,
    }
    if meta is not None:
        payload["meta"] = meta
    return jsonify(payload), status_code


def api_error(
    code: str = "BAD_REQUEST",
    message: str = "An error occurred",
    details: Any = None,
    status_code: int = 400
) -> tuple[Response, int]:
    """
    Standard error JSON response envelope for SubFlow APIs.
    """
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        }
    }
    return jsonify(payload), status_code
