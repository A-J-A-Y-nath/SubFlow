from typing import Any, Dict, List
from flask import request


def get_pagination_params(default_per_page: int = 20, max_per_page: int = 100) -> tuple[int, int]:
    """Extract page and per_page parameters from the request query string."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", default_per_page))
        per_page = max(1, min(per_page, max_per_page))
    except (ValueError, TypeError):
        per_page = default_per_page

    return page, per_page


def paginate_query(query, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query and return a structured dictionary with items and metadata.
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return {
        "items": [item.to_dict() if hasattr(item, "to_dict") else item for item in items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
    }
