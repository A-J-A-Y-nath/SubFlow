from flask import Flask
from backend.routes.auth import auth_bp
from backend.routes.health import health_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.products import products_bp
from backend.routes.plans import plans_bp
from backend.routes.subscriptions import subscriptions_bp
from backend.routes.quotations import quotations_bp
from backend.routes.invoices import invoices_bp
from backend.routes.payments import payments_bp
from backend.routes.discounts import discounts_bp
from backend.routes.reports import reports_bp
from backend.routes.billing import billing_bp
from backend.routes.customers import customers_bp


def register_routes(app: Flask):
    """Register all API v1 routes with uniform URL prefix."""
    prefix = app.config.get("API_PREFIX", "/api/v1")

    app.register_blueprint(health_bp, url_prefix=prefix)
    app.register_blueprint(auth_bp, url_prefix=f"{prefix}/auth")
    app.register_blueprint(dashboard_bp, url_prefix=f"{prefix}/dashboard")
    app.register_blueprint(products_bp, url_prefix=f"{prefix}/products")
    app.register_blueprint(plans_bp, url_prefix=f"{prefix}/plans")
    app.register_blueprint(subscriptions_bp, url_prefix=f"{prefix}/subscriptions")
    app.register_blueprint(quotations_bp, url_prefix=f"{prefix}/quotations")
    app.register_blueprint(invoices_bp, url_prefix=f"{prefix}/invoices")
    app.register_blueprint(payments_bp, url_prefix=f"{prefix}/payments")
    app.register_blueprint(discounts_bp, url_prefix=f"{prefix}/discounts")
    app.register_blueprint(reports_bp, url_prefix=f"{prefix}/reports")
    app.register_blueprint(billing_bp, url_prefix=f"{prefix}/billing")
    app.register_blueprint(customers_bp, url_prefix=f"{prefix}/customers")
