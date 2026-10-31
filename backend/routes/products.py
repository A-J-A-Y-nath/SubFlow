from flask import Blueprint, request
from backend.models.product import Product
from backend.utils.response import api_response
from backend.utils.pagination import paginate_query, get_pagination_params
from backend.utils.decorators import role_required, ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER

products_bp = Blueprint("products", __name__, url_prefix="/products")


@products_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER)
def list_products():
    """
    List products with pagination and optional search filter.
    Developer Note: Extend with variant filtering and category management.
    """
    page, per_page = get_pagination_params()
    query = Product.query

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
    """Retrieve single product details."""
    product = Product.query.get_or_404(product_id)
    return api_response(data=product.to_dict(), message="Product retrieved")
