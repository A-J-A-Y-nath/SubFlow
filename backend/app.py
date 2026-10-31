import os
from flask import Flask, jsonify
from backend.config import config_by_name
from backend.extensions import db, migrate, jwt, cors
from backend.routes import register_routes
from backend.utils.response import api_error


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory for SubFlow Flask backend.
    """
    app = Flask(__name__)

    # Determine configuration profile
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    config_class = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Register all routes with /api/v1 prefix
    register_routes(app)

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return api_error(
            code="TOKEN_EXPIRED",
            message="Your session has expired. Please log in again.",
            status_code=401
        )

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return api_error(
            code="INVALID_TOKEN",
            message="The provided authorization token is invalid.",
            details=error_string,
            status_code=401
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return api_error(
            code="AUTHORIZATION_REQUIRED",
            message="Authorization token is missing. Please provide a Bearer token in the header.",
            details=error_string,
            status_code=401
        )

    # General HTTP error handlers
    @app.errorhandler(400)
    def handle_bad_request(e):
        return api_error(code="BAD_REQUEST", message=str(e), status_code=400)

    @app.errorhandler(404)
    def handle_not_found(e):
        return api_error(code="NOT_FOUND", message="The requested resource or endpoint was not found", status_code=404)

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return api_error(code="METHOD_NOT_ALLOWED", message="The requested HTTP method is not allowed on this endpoint", status_code=405)

    @app.errorhandler(500)
    def handle_server_error(e):
        return api_error(code="INTERNAL_SERVER_ERROR", message="An unexpected internal server error occurred", status_code=500)

    # CLI Seed Command for rapid local testing & hackathon evaluation
    @app.cli.command("seed")
    def seed_db():
        """Seed the database with initial demo accounts and starter records."""
        from backend.models import User, Customer, Plan, Product, ProductVariant

        # 1. Create default Admin user
        admin = User.query.filter_by(email="admin@subflow.io").first()
        if not admin:
            admin = User(
                email="admin@subflow.io",
                first_name="Admin",
                last_name="User",
                role="admin",
                is_active=True
            )
            admin.set_password("SubFlow#Admin2026!")
            db.session.add(admin)
            print("[+] Created admin: admin@subflow.io (pwd: SubFlow#Admin2026!)")

        # 2. Create default Staff user
        staff = User.query.filter_by(email="staff@subflow.io").first()
        if not staff:
            staff = User(
                email="staff@subflow.io",
                first_name="Staff",
                last_name="Member",
                role="staff",
                is_active=True
            )
            staff.set_password("SubFlow#Staff2026!")
            db.session.add(staff)
            print("[+] Created staff: staff@subflow.io (pwd: SubFlow#Staff2026!)")

        # 3. Create default Customer user
        customer_user = User.query.filter_by(email="customer@subflow.io").first()
        if not customer_user:
            customer_user = User(
                email="customer@subflow.io",
                first_name="Acme",
                last_name="Corp",
                role="customer",
                is_active=True
            )
            customer_user.set_password("SubFlow#Customer2026!")
            db.session.add(customer_user)
            db.session.flush()

            customer_profile = Customer(
                user_id=customer_user.id,
                company_name="Acme Corporation",
                contact_name="Acme Representative",
                email="customer@subflow.io",
                billing_country="United States",
                currency="USD",
                payment_terms_days=30
            )
            db.session.add(customer_profile)
            print("[+] Created customer: customer@subflow.io (pwd: SubFlow#Customer2026!)")

        # 4. Create starter Plans
        if Plan.query.count() == 0:
            plan_starter = Plan(
                name="Starter Plan",
                code="PLAN-STARTER-MO",
                description="Ideal for early-stage startups and small teams",
                billing_interval="monthly",
                billing_interval_count=1,
                base_price=29.00,
                trial_days=14,
                features=["Up to 5 users", "Basic Analytics", "Standard Support", "1 Workspace"],
                is_active=True
            )
            plan_pro = Plan(
                name="Professional Plan",
                code="PLAN-PRO-MO",
                description="Full-featured subscription for growing businesses",
                billing_interval="monthly",
                billing_interval_count=1,
                base_price=99.00,
                trial_days=14,
                features=["Up to 25 users", "Advanced Analytics", "Priority Support", "Unlimited Workspaces", "Custom Webhooks"],
                is_active=True
            )
            plan_enterprise = Plan(
                name="Enterprise Annual",
                code="PLAN-ENT-YR",
                description="Dedicated infrastructure, SLA, and custom integration",
                billing_interval="yearly",
                billing_interval_count=1,
                base_price=999.00,
                trial_days=30,
                features=["Unlimited users", "Dedicated Account Manager", "99.99% Uptime SLA", "Custom Invoicing", "Audit Log Export"],
                is_active=True
            )
            db.session.add_all([plan_starter, plan_pro, plan_enterprise])
            print("[+] Created default plans: Starter, Professional, Enterprise")

        # 5. Create starter Products
        if Product.query.count() == 0:
            prod_seat = Product(
                name="Additional User Seat",
                sku="PROD-SEAT-ADDON",
                description="Add extra collaborator seats to any active plan",
                is_recurring=True,
                default_price=10.00,
                unit_of_measure="seat"
            )
            prod_storage = Product(
                name="Cloud Storage 100GB",
                sku="PROD-STORAGE-100GB",
                description="Dedicated cloud backup and artifact retention storage",
                is_recurring=True,
                default_price=20.00,
                unit_of_measure="unit"
            )
            db.session.add_all([prod_seat, prod_storage])
            print("[+] Created default products: Additional Seat, Cloud Storage")

        db.session.commit()
        print("[+] Database seeding complete!")

    # CLI Recurring Billing execution command
    @app.cli.command("recurring-billing")
    def recurring_billing_cmd():
        """Execute recurring billing generation for all due subscriptions."""
        from datetime import date
        from backend.services.billing_service import BillingService

        today = date.today()
        print(f"[*] Running recurring billing generation for target date: {today}...")
        results = BillingService.generate_recurring_invoices(target_date=today)
        print(f"[+] Total due subscriptions: {results['total_due_subscriptions']}")
        print(f"[+] Invoices generated: {len(results['generated_invoices'])}")
        print(f"[-] Skipped: {len(results['skipped'])}")
        if results["errors"]:
            print(f"[!] Encountered {len(results['errors'])} errors during processing:")
            for err in results["errors"]:
                print(f"    - Sub #{err['subscription_number']}: {err['error']}")
        print("[*] Recurring billing execution complete.")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
