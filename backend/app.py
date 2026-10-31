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
        from datetime import datetime, date, timedelta, timezone
        from decimal import Decimal
        from backend.models import (
            User, Customer, Plan, Product, ProductVariant,
            Subscription, SubscriptionLine,
            Invoice, InvoiceLine,
            Payment, PaymentAllocation,
            DiscountRule
        )

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

        # 6. Create secondary Customer profile for multi-tenant testing
        techstart = Customer.query.filter_by(email="contact@techstart.io").first()
        if not techstart:
            techstart = Customer(
                company_name="TechStart Dynamics Inc.",
                contact_name="Elena Rostova",
                email="contact@techstart.io",
                phone="+1 (555) 349-8821",
                billing_street="404 Innovation Way",
                billing_city="Austin",
                billing_state="TX",
                billing_postal_code="78701",
                billing_country="United States",
                currency="USD",
                payment_terms_days=15,
                credit_limit=Decimal("5000.00"),
                is_active=True
            )
            db.session.add(techstart)
            db.session.flush()
            print("[+] Created enterprise customer: TechStart Dynamics Inc.")

        # 7. Create starter Subscriptions
        today = date.today()
        pro_plan = Plan.query.filter_by(code="PLAN-PRO-MO").first()
        starter_plan = Plan.query.filter_by(code="PLAN-STARTER-MO").first()
        ent_plan = Plan.query.filter_by(code="PLAN-ENT-YR").first()
        customer_acme = Customer.query.filter_by(email="customer@subflow.io").first()

        sub1 = Subscription.query.filter_by(subscription_number="SUB-2026-0001").first()
        if not sub1 and customer_acme and pro_plan:
            sub1 = Subscription(
                subscription_number="SUB-2026-0001",
                customer_id=customer_acme.id,
                plan_id=pro_plan.id,
                status="active",
                start_date=today - timedelta(days=60),
                current_period_start=today - timedelta(days=30),
                current_period_end=today,
                next_billing_date=today,
                auto_renew=True,
                recurring_amount=Decimal("99.00"),
                currency="USD"
            )
            sub2 = Subscription(
                subscription_number="SUB-2026-0002",
                customer_id=customer_acme.id,
                plan_id=starter_plan.id,
                status="active",
                start_date=today - timedelta(days=90),
                current_period_start=today - timedelta(days=15),
                current_period_end=today + timedelta(days=15),
                next_billing_date=today + timedelta(days=15),
                auto_renew=True,
                recurring_amount=Decimal("29.00"),
                currency="USD"
            )
            sub3 = Subscription(
                subscription_number="SUB-2026-0003",
                customer_id=techstart.id,
                plan_id=ent_plan.id,
                status="active",
                start_date=today - timedelta(days=45),
                current_period_start=today - timedelta(days=45),
                current_period_end=today + timedelta(days=320),
                next_billing_date=today + timedelta(days=320),
                auto_renew=True,
                recurring_amount=Decimal("999.00"),
                currency="USD"
            )
            db.session.add_all([sub1, sub2, sub3])
            db.session.flush()
            print("[+] Created active subscriptions: SUB-2026-0001, SUB-2026-0002, SUB-2026-0003")

        # 8. Create Discount Rules
        if DiscountRule.query.count() == 0:
            disc_save20 = DiscountRule(
                code="SAVE20",
                name="20% Off Growth Promotion",
                description="20% discount on orders up to $50 max savings",
                discount_type="percentage",
                value=Decimal("20.00"),
                min_order_amount=Decimal("50.00"),
                max_discount_amount=Decimal("50.00"),
                valid_from=datetime.now(timezone.utc) - timedelta(days=30),
                valid_to=datetime.now(timezone.utc) + timedelta(days=60),
                max_uses=100,
                current_uses=5,
                is_active=True
            )
            disc_startup50 = DiscountRule(
                code="STARTUP50",
                name="$50 Startup Credit",
                description="Flat $50 discount on orders exceeding $100",
                discount_type="fixed",
                value=Decimal("50.00"),
                min_order_amount=Decimal("100.00"),
                max_discount_amount=None,
                valid_from=datetime.now(timezone.utc) - timedelta(days=15),
                valid_to=datetime.now(timezone.utc) + timedelta(days=45),
                max_uses=50,
                current_uses=2,
                is_active=True
            )
            disc_welcome10 = DiscountRule(
                code="WELCOME10",
                name="Welcome New Subscriber",
                description="10% off recurring subscriptions",
                discount_type="percentage",
                value=Decimal("10.00"),
                min_order_amount=Decimal("0.00"),
                max_discount_amount=None,
                is_active=True
            )
            disc_expired = DiscountRule(
                code="EXPIRED25",
                name="Winter Holiday 25%",
                description="Expired promotional rule for validation testing",
                discount_type="percentage",
                value=Decimal("25.00"),
                valid_from=datetime.now(timezone.utc) - timedelta(days=45),
                valid_to=datetime.now(timezone.utc) - timedelta(days=10),
                is_active=False
            )
            db.session.add_all([disc_save20, disc_startup50, disc_welcome10, disc_expired])
            print("[+] Created discount rules: SAVE20, STARTUP50, WELCOME10, EXPIRED25")

        # 9. Create Operational Invoices & Lines
        inv1 = Invoice.query.filter_by(invoice_number="INV-2026-0001").first()
        if not inv1 and customer_acme and sub1:
            inv1 = Invoice(
                invoice_number="INV-2026-0001",
                customer_id=customer_acme.id,
                subscription_id=sub1.id,
                status="paid",
                invoice_date=today - timedelta(days=60),
                due_date=today - timedelta(days=30),
                currency="USD",
                subtotal=Decimal("99.00"),
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("99.00"),
                amount_paid=Decimal("99.00"),
                balance_due=Decimal("0.00"),
                payment_terms="Net 30",
                notes="Initial billing cycle for Professional Subscription"
            )
            db.session.add(inv1)
            db.session.flush()

            inv1_line = InvoiceLine(
                invoice_id=inv1.id,
                description="Professional Plan - Monthly Recurring",
                quantity=Decimal("1.00"),
                unit_price=Decimal("99.00"),
                discount_percent=Decimal("0.00"),
                line_total=Decimal("99.00")
            )
            db.session.add(inv1_line)

            # Invoice 2: Partially Paid
            inv2 = Invoice(
                invoice_number="INV-2026-0002",
                customer_id=customer_acme.id,
                subscription_id=sub1.id,
                status="partial",
                invoice_date=today - timedelta(days=30),
                due_date=today - timedelta(days=10),
                currency="USD",
                subtotal=Decimal("150.00"),
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("150.00"),
                amount_paid=Decimal("50.00"),
                balance_due=Decimal("100.00"),
                payment_terms="Net 30",
                notes="Renewal billing cycle + 2 additional user seats"
            )
            db.session.add(inv2)
            db.session.flush()

            inv2_l1 = InvoiceLine(
                invoice_id=inv2.id,
                description="Professional Plan - Monthly Recurring",
                quantity=Decimal("1.00"),
                unit_price=Decimal("99.00"),
                discount_percent=Decimal("0.00"),
                line_total=Decimal("99.00")
            )
            inv2_l2 = InvoiceLine(
                invoice_id=inv2.id,
                description="Additional User Seat",
                quantity=Decimal("3.00"),
                unit_price=Decimal("17.00"),
                discount_percent=Decimal("0.00"),
                line_total=Decimal("51.00")
            )
            db.session.add_all([inv2_l1, inv2_l2])

            # Invoice 3: Posted / Issued (Current)
            inv3 = Invoice(
                invoice_number="INV-2026-0003",
                customer_id=customer_acme.id,
                subscription_id=sub2.id,
                status="posted",
                invoice_date=today - timedelta(days=5),
                due_date=today + timedelta(days=25),
                currency="USD",
                subtotal=Decimal("29.00"),
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("29.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("29.00"),
                payment_terms="Net 30",
                notes="Starter Plan - Secondary Workspace"
            )
            db.session.add(inv3)
            db.session.flush()

            inv3_line = InvoiceLine(
                invoice_id=inv3.id,
                description="Starter Plan - Monthly",
                quantity=Decimal("1.00"),
                unit_price=Decimal("29.00"),
                discount_percent=Decimal("0.00"),
                line_total=Decimal("29.00")
            )
            db.session.add(inv3_line)

            # Invoice 4: Overdue
            inv4 = Invoice(
                invoice_number="INV-2026-0004",
                customer_id=customer_acme.id,
                subscription_id=None,
                status="overdue",
                invoice_date=today - timedelta(days=45),
                due_date=today - timedelta(days=15),
                currency="USD",
                subtotal=Decimal("99.00"),
                discount_amount=Decimal("0.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("99.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("99.00"),
                payment_terms="Net 30",
                notes="Priority Support Implementation & Onboarding Session"
            )
            db.session.add(inv4)
            db.session.flush()

            inv4_line = InvoiceLine(
                invoice_id=inv4.id,
                description="Priority Onboarding & Architecture Session",
                quantity=Decimal("1.00"),
                unit_price=Decimal("99.00"),
                discount_percent=Decimal("0.00"),
                line_total=Decimal("99.00")
            )
            db.session.add(inv4_line)

            # Invoice 5: Draft (TechStart Dynamics)
            inv5 = Invoice(
                invoice_number="INV-2026-0005",
                customer_id=techstart.id,
                subscription_id=sub3.id,
                status="draft",
                invoice_date=today,
                due_date=today + timedelta(days=15),
                currency="USD",
                subtotal=Decimal("999.00"),
                discount_amount=Decimal("50.00"),
                tax_amount=Decimal("0.00"),
                total_amount=Decimal("949.00"),
                amount_paid=Decimal("0.00"),
                balance_due=Decimal("949.00"),
                payment_terms="Net 15",
                notes="Enterprise Annual Subscription - Awaiting Approval"
            )
            db.session.add(inv5)
            db.session.flush()

            inv5_line = InvoiceLine(
                invoice_id=inv5.id,
                description="Enterprise Annual License (365 Days)",
                quantity=Decimal("1.00"),
                unit_price=Decimal("999.00"),
                discount_percent=Decimal("5.00"),
                line_total=Decimal("949.05")
            )
            db.session.add(inv5_line)
            print("[+] Created operational invoices: INV-2026-0001 (paid), INV-2026-0002 (partial), INV-2026-0003 (posted), INV-2026-0004 (overdue), INV-2026-0005 (draft)")

        # 10. Create Payments and Allocations
        if Payment.query.count() == 0 and inv1 and inv2:
            pay1 = Payment(
                payment_number="PAY-2026-0001",
                customer_id=customer_acme.id,
                amount=Decimal("99.00"),
                currency="USD",
                payment_method="stripe",
                transaction_reference="ch_3MtestStripe0001",
                status="completed",
                payment_date=datetime.now(timezone.utc) - timedelta(days=35),
                notes="Automated card billing via Stripe"
            )
            db.session.add(pay1)
            db.session.flush()

            alloc1 = PaymentAllocation(
                payment_id=pay1.id,
                invoice_id=inv1.id,
                amount_allocated=Decimal("99.00")
            )
            db.session.add(alloc1)

            # Payment 2: Partial Bank Transfer
            pay2 = Payment(
                payment_number="PAY-2026-0002",
                customer_id=customer_acme.id,
                amount=Decimal("50.00"),
                currency="USD",
                payment_method="bank_transfer",
                transaction_reference="wire_ach_884920",
                status="completed",
                payment_date=datetime.now(timezone.utc) - timedelta(days=8),
                notes="Wire transfer received from Acme Treasury"
            )
            db.session.add(pay2)
            db.session.flush()

            alloc2 = PaymentAllocation(
                payment_id=pay2.id,
                invoice_id=inv2.id,
                amount_allocated=Decimal("50.00")
            )
            db.session.add(alloc2)

            # Payment 3: Unallocated credit
            pay3 = Payment(
                payment_number="PAY-2026-0003",
                customer_id=customer_acme.id,
                amount=Decimal("100.00"),
                currency="USD",
                payment_method="credit_card",
                transaction_reference="auth_card_991823",
                status="completed",
                payment_date=datetime.now(timezone.utc) - timedelta(days=2),
                notes="Prepayment deposit on customer account"
            )
            db.session.add(pay3)
            print("[+] Created payments: PAY-2026-0001 ($99 allocated), PAY-2026-0002 ($50 allocated), PAY-2026-0003 ($100 unallocated deposit)")

        db.session.commit()
        print("[+] Database seeding complete!")

    # CLI Recurring Billing execution command
    import click
    @app.cli.command("recurring-billing")
    @click.option("--dry-run", is_flag=True, help="Preview invoice generation without writing to database")
    @click.option("--target-date", type=str, default=None, help="Target billing date YYYY-MM-DD (defaults to today)")
    def recurring_billing_cmd(dry_run, target_date):
        """Execute recurring billing generation for all due subscriptions."""
        from datetime import date
        from backend.services.billing_service import BillingService

        if target_date:
            try:
                t_date = date.fromisoformat(target_date)
            except ValueError:
                print(f"[!] Invalid target date format '{target_date}'. Expected YYYY-MM-DD.")
                return
        else:
            t_date = date.today()

        mode_str = " (DRY RUN PREVIEW)" if dry_run else ""
        print(f"[*] Running recurring billing generation for target date: {t_date}{mode_str}...")
        results = BillingService.generate_recurring_invoices(target_date=t_date, dry_run=dry_run)
        print(f"[+] Total due subscriptions: {results['total_due_subscriptions']}")
        print(f"[+] Invoices generated: {len(results['generated_invoices'])}")
        print(f"[-] Skipped: {len(results['skipped'])}")
        if results.get("errors"):
            print(f"[!] Encountered {len(results['errors'])} errors during processing:")
            for err in results["errors"]:
                print(f"    - Sub #{err['subscription_number']}: {err['error']}")
        print(f"[*] Recurring billing execution complete{mode_str}.")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
