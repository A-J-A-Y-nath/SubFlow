from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
import calendar
from sqlalchemy import func
from backend.extensions import db
from backend.models.invoice import Invoice, InvoiceLine
from backend.models.subscription import Subscription
from backend.models.customer import Customer
from backend.models.plan import Plan
from backend.models.product import Product
from backend.models.audit_log import AuditLog
from backend.services.discount_service import DiscountService, to_decimal

TWO_PLACES = Decimal("0.01")


def advance_date_by_interval(start_date: date, interval: str, count: int = 1) -> date:
    """
    Safely advances a date by a given cadence: daily, weekly, monthly, quarterly, yearly.
    Handles month-end boundary conditions (e.g. Jan 31 -> Feb 28).
    """
    interval = (interval or "monthly").lower().strip()
    count = max(1, count)

    if interval == "daily":
        return start_date + timedelta(days=count)
    elif interval == "weekly":
        return start_date + timedelta(weeks=count)
    elif interval in ("monthly", "quarterly", "yearly"):
        months_to_add = count
        if interval == "quarterly":
            months_to_add = count * 3
        elif interval == "yearly":
            months_to_add = count * 12

        year = start_date.year + (start_date.month + months_to_add - 1) // 12
        month = (start_date.month + months_to_add - 1) % 12 + 1
        # Handle month length mismatch (e.g. Aug 31 -> Sep 30)
        max_day = calendar.monthrange(year, month)[1]
        day = min(start_date.day, max_day)
        return date(year, month, day)
    else:
        # Default monthly fallback
        year = start_date.year + (start_date.month + count - 1) // 12
        month = (start_date.month + count - 1) % 12 + 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(start_date.day, max_day)
        return date(year, month, day)


class BillingService:
    @staticmethod
    def generate_invoice_number() -> str:
        """
        Generates a unique, sequential invoice number: INV-YYYY-XXXX.
        """
        current_year = datetime.now(timezone.utc).year
        prefix = f"INV-{current_year}-"

        # Find latest invoice number for current year
        latest = (
            db.session.query(Invoice.invoice_number)
            .filter(Invoice.invoice_number.like(f"{prefix}%"))
            .order_by(Invoice.id.desc())
            .first()
        )

        next_seq = 1
        if latest and latest[0]:
            try:
                seq_str = latest[0].replace(prefix, "")
                next_seq = int(seq_str) + 1
            except (ValueError, TypeError):
                # Fallback to total count + 1
                next_seq = Invoice.query.count() + 1

        invoice_number = f"{prefix}{next_seq:04d}"
        # Ensure absolute uniqueness in case of gaps
        while Invoice.query.filter_by(invoice_number=invoice_number).first() is not None:
            next_seq += 1
            invoice_number = f"{prefix}{next_seq:04d}"

        return invoice_number

    @staticmethod
    def calculate_line(
        quantity: Decimal | float | int,
        unit_price: Decimal | float | int,
        discount_percent: Decimal | float | int = 0.0
    ) -> Decimal:
        """Calculate line item total using Decimal arithmetic."""
        qty_dec = to_decimal(quantity)
        price_dec = to_decimal(unit_price)
        disc_dec = to_decimal(discount_percent)

        if qty_dec <= Decimal("0.00"):
            raise ValueError("Quantity must be greater than zero")
        if price_dec < Decimal("0.00"):
            raise ValueError("Unit price cannot be negative")
        if disc_dec < Decimal("0.00") or disc_dec > Decimal("100.00"):
            raise ValueError("Discount percent must be between 0 and 100")

        gross = qty_dec * price_dec
        discount_multiplier = (Decimal("100.00") - disc_dec) / Decimal("100.00")
        line_total = (gross * discount_multiplier).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return max(Decimal("0.00"), line_total)

    @classmethod
    def calculate_invoice_totals(
        cls,
        lines_data: List[Dict[str, Any]],
        discount_amount: Decimal = Decimal("0.00"),
        tax_amount: Decimal = Decimal("0.00")
    ) -> Dict[str, Decimal]:
        """
        Recalculates all invoice financials from verified line items.
        """
        subtotal = Decimal("0.00")
        calculated_lines = []

        for line in lines_data:
            qty = to_decimal(line.get("quantity", 1))
            price = to_decimal(line.get("unit_price", 0))
            disc_pct = to_decimal(line.get("discount_percent", 0))
            line_total = cls.calculate_line(qty, price, disc_pct)
            subtotal += line_total
            calculated_lines.append({
                **line,
                "quantity": qty,
                "unit_price": price,
                "discount_percent": disc_pct,
                "line_total": line_total
            })

        subtotal = subtotal.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        discount_amount = min(to_decimal(discount_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP), subtotal)
        tax_amount = max(Decimal("0.00"), to_decimal(tax_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))
        total_amount = max(Decimal("0.00"), (subtotal - discount_amount + tax_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))

        return {
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "balance_due": total_amount,
            "amount_paid": Decimal("0.00"),
            "lines": calculated_lines
        }

    @classmethod
    def create_invoice(
        cls,
        customer_id: int,
        invoice_date: date,
        due_date: date,
        lines: List[Dict[str, Any]],
        subscription_id: Optional[int] = None,
        quotation_id: Optional[int] = None,
        coupon_code: Optional[str] = None,
        tax_amount: Decimal = Decimal("0.00"),
        notes: Optional[str] = None,
        payment_terms: str = "Net 30",
        currency: str = "USD",
        status: str = "draft",
        user_id: Optional[int] = None
    ) -> Invoice:
        """
        Creates and persists a validated invoice with line items.
        """
        customer = db.session.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer with ID {customer_id} does not exist")

        if not lines or len(lines) == 0:
            raise ValueError("Invoice must contain at least one line item")

        # Validate line items exist in catalog if product_id is supplied
        for line in lines:
            prod_id = line.get("product_id")
            if prod_id:
                prod = db.session.get(Product, prod_id)
                if not prod:
                    raise ValueError(f"Product ID {prod_id} not found")

        # Pre-calculate subtotal to check coupon qualification
        raw_subtotal = Decimal("0.00")
        for line in lines:
            raw_subtotal += cls.calculate_line(
                line.get("quantity", 1),
                line.get("unit_price", 0),
                line.get("discount_percent", 0)
            )

        # Coupon validation
        discount_amount = Decimal("0.00")
        discount_rule = None
        if coupon_code:
            is_valid, disc_val, rule, err_msg = DiscountService.validate_and_calculate_discount(
                code=coupon_code,
                eligible_amount=raw_subtotal
            )
            if not is_valid:
                raise ValueError(err_msg or "Invalid coupon code")
            discount_amount = disc_val
            discount_rule = rule

        totals = cls.calculate_invoice_totals(
            lines_data=lines,
            discount_amount=discount_amount,
            tax_amount=tax_amount
        )

        inv_num = cls.generate_invoice_number()
        invoice = Invoice(
            invoice_number=inv_num,
            customer_id=customer.id,
            subscription_id=subscription_id,
            quotation_id=quotation_id,
            status=status,
            invoice_date=invoice_date,
            due_date=due_date,
            currency=currency or customer.currency or "USD",
            subtotal=totals["subtotal"],
            discount_amount=totals["discount_amount"],
            tax_amount=totals["tax_amount"],
            total_amount=totals["total_amount"],
            amount_paid=Decimal("0.00"),
            balance_due=totals["total_amount"],
            notes=notes,
            payment_terms=payment_terms or f"Net {customer.payment_terms_days}"
        )
        db.session.add(invoice)
        db.session.flush()

        # Add invoice lines
        for item in totals["lines"]:
            inv_line = InvoiceLine(
                invoice_id=invoice.id,
                product_id=item.get("product_id"),
                description=item.get("description", "Subscription line item"),
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount_percent=item["discount_percent"],
                line_total=item["line_total"]
            )
            db.session.add(inv_line)

        # If coupon was redeemed, record usage count
        if discount_rule:
            DiscountService.record_usage(discount_rule.id)

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action="INVOICE_CREATED",
            entity_type="Invoice",
            entity_id=str(invoice.id),
            new_values={
                "invoice_number": invoice.invoice_number,
                "customer_id": invoice.customer_id,
                "total_amount": float(invoice.total_amount),
                "status": invoice.status
            }
        )
        db.session.add(audit)
        return invoice

    @classmethod
    def generate_recurring_invoices(
        cls,
        target_date: Optional[date] = None,
        dry_run: bool = False,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Recurring billing engine.
        Identifies eligible active subscriptions whose next_billing_date <= target_date,
        generates non-duplicate invoices, advances billing schedules, and commits safely.
        """
        if target_date is None:
            target_date = date.today()

        # Query eligible subscriptions
        query = Subscription.query.filter(
            Subscription.status == "active",
            Subscription.auto_renew.is_(True),
            Subscription.next_billing_date <= target_date
        )

        subscriptions = query.all()

        results = {
            "target_date": target_date.isoformat(),
            "dry_run": dry_run,
            "total_due_subscriptions": len(subscriptions),
            "generated_invoices": [],
            "skipped": [],
            "errors": []
        }

        for sub in subscriptions:
            # 1. Trial period exclusion
            if sub.trial_end and sub.trial_end > target_date:
                results["skipped"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "reason": f"Subscription in active trial until {sub.trial_end.isoformat()}"
                })
                continue

            # 2. Duplicate Prevention / Idempotency check:
            # Check if an uncancelled invoice already exists for this subscription and billing cycle
            existing_inv = Invoice.query.filter(
                Invoice.subscription_id == sub.id,
                Invoice.status != "cancelled",
                Invoice.invoice_date == sub.next_billing_date
            ).first()

            if existing_inv:
                results["skipped"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "reason": f"Invoice {existing_inv.invoice_number} already generated for billing date {sub.next_billing_date.isoformat()}"
                })
                continue

            try:
                # 3. Assemble Line Items
                plan = sub.plan
                lines = []
                if sub.lines and len(sub.lines) > 0:
                    for sl in sub.lines:
                        lines.append({
                            "product_id": sl.product_id,
                            "description": sl.description or f"{plan.name} - Component",
                            "quantity": sl.quantity,
                            "unit_price": sl.unit_price,
                            "discount_percent": sl.discount_percent
                        })
                else:
                    # Fallback to subscription plan base price
                    lines.append({
                        "product_id": None,
                        "description": f"{plan.name} Recurring Subscription",
                        "quantity": Decimal("1.00"),
                        "unit_price": to_decimal(sub.recurring_amount or plan.base_price),
                        "discount_percent": Decimal("0.00")
                    })

                customer = sub.customer
                inv_date = sub.next_billing_date or target_date
                terms_days = customer.payment_terms_days if customer else 30
                due_date = inv_date + timedelta(days=terms_days)

                if dry_run:
                    totals = cls.calculate_invoice_totals(lines)
                    results["generated_invoices"].append({
                        "subscription_id": sub.id,
                        "subscription_number": sub.subscription_number,
                        "customer_id": sub.customer_id,
                        "customer_name": customer.company_name if customer else None,
                        "invoice_date": inv_date.isoformat(),
                        "due_date": due_date.isoformat(),
                        "estimated_total": float(totals["total_amount"]),
                        "mode": "DRY_RUN_PREVIEW"
                    })
                    continue

                # 4. Generate Invoice (Issued / Posted)
                invoice = cls.create_invoice(
                    customer_id=sub.customer_id,
                    invoice_date=inv_date,
                    due_date=due_date,
                    lines=lines,
                    subscription_id=sub.id,
                    quotation_id=sub.quotation_id,
                    status="posted",
                    currency=sub.currency or customer.currency or "USD",
                    payment_terms=f"Net {terms_days}",
                    notes=f"Recurring billing cycle: {sub.current_period_start.isoformat()} to {sub.current_period_end.isoformat()}",
                    user_id=user_id
                )

                # 5. Advance Subscription Billing Period
                interval = plan.billing_interval if plan else "monthly"
                interval_count = plan.billing_interval_count if plan else 1

                new_period_start = sub.current_period_end
                new_period_end = advance_date_by_interval(new_period_start, interval, interval_count)
                new_next_billing = new_period_end

                sub.current_period_start = new_period_start
                sub.current_period_end = new_period_end
                sub.next_billing_date = new_next_billing

                db.session.commit()

                results["generated_invoices"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "total_amount": float(invoice.total_amount),
                    "new_next_billing_date": new_next_billing.isoformat()
                })

            except Exception as e:
                db.session.rollback()
                results["errors"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "error": str(e)
                })

        return results
