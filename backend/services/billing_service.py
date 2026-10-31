"""
SubFlow Financial & Billing Services
"""
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
import calendar
import logging
from sqlalchemy import func
from backend.extensions import db
from backend.models.invoice import Invoice, InvoiceLine
from backend.models.subscription import Subscription
from backend.models.customer import Customer
from backend.models.plan import Plan
from backend.models.product import Product
from backend.models.audit_log import AuditLog
from backend.services.discount_service import DiscountService, to_decimal
from backend.services.invoice_service import create_invoice_from_subscription
from backend.services.subscription_service import _compute_period_end

logger = logging.getLogger(__name__)

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
        max_day = calendar.monthrange(year, month)[1]
        day = min(start_date.day, max_day)
        return date(year, month, day)
    else:
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
                next_seq = Invoice.query.count() + 1

        invoice_number = f"{prefix}{next_seq:04d}"
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
        coupon_code: Optional[str] = None,
        customer_id: Optional[int] = None,
        tax_amount: Decimal | float | int = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates subtotal, discount, tax, and final total for an invoice with Decimal accuracy.
        """
        subtotal = Decimal("0.00")
        processed_lines = []

        for idx, line in enumerate(lines_data):
            qty = to_decimal(line.get("quantity", 1))
            price = to_decimal(line.get("unit_price", 0))
            disc_pct = to_decimal(line.get("discount_percent", 0))

            line_subtotal = (qty * price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            disc_amount = (line_subtotal * (disc_pct / Decimal("100.00"))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            line_total = (line_subtotal - disc_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            subtotal += line_total
            processed_lines.append({
                "product_id": line.get("product_id"),
                "description": line.get("description", f"Line item {idx + 1}"),
                "quantity": qty,
                "unit_price": price,
                "discount_percent": disc_pct,
                "amount": line_total
            })

        coupon_discount = Decimal("0.00")
        applied_coupon = None
        if coupon_code and coupon_code.strip():
            validation = DiscountService.validate_coupon(coupon_code, subtotal, customer_id)
            if validation["valid"]:
                coupon_discount = to_decimal(validation["discount_amount"])
                applied_coupon = validation["discount"]
            else:
                raise ValueError(f"Invalid coupon: {validation['message']}")

        tax_dec = to_decimal(tax_amount)
        if tax_dec < Decimal("0.00"):
            raise ValueError("Tax amount cannot be negative")

        total = max(Decimal("0.00"), subtotal - coupon_discount + tax_dec).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return {
            "subtotal": subtotal,
            "discount_amount": coupon_discount,
            "tax_amount": tax_dec,
            "total_amount": total,
            "lines": processed_lines,
            "applied_coupon": applied_coupon
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
        tax_amount: Decimal | float | int = 0.0,
        currency: str = "USD",
        payment_terms: str = "Net 30",
        notes: Optional[str] = None,
        status: str = "draft",
        user_id: Optional[int] = None
    ) -> Invoice:
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer with id {customer_id} not found")

        if due_date < invoice_date:
            raise ValueError("Due date cannot precede invoice date")

        if not lines:
            raise ValueError("An invoice must contain at least one line item")

        totals = cls.calculate_invoice_totals(
            lines_data=lines,
            coupon_code=coupon_code,
            customer_id=customer_id,
            tax_amount=tax_amount
        )

        invoice_number = cls.generate_invoice_number()

        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=customer_id,
            subscription_id=subscription_id,
            quotation_id=quotation_id,
            status=status,
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=totals["subtotal"],
            tax_amount=totals["tax_amount"],
            discount_amount=totals["discount_amount"],
            total_amount=totals["total_amount"],
            amount_paid=Decimal("0.00"),
            balance_due=totals["total_amount"],
            currency=currency or customer.currency or "USD",
            payment_terms=payment_terms,
            notes=notes
        )

        for line_item in totals["lines"]:
            inv_line = InvoiceLine(
                product_id=line_item["product_id"],
                description=line_item["description"],
                quantity=line_item["quantity"],
                unit_price=line_item["unit_price"],
                discount_percent=line_item["discount_percent"],
                amount=line_item["amount"]
            )
            invoice.lines.append(inv_line)

        db.session.add(invoice)
        db.session.flush()

        if coupon_code and totals.get("applied_coupon"):
            DiscountService.record_coupon_usage(totals["applied_coupon"]["id"], invoice.id)

        AuditLog.log_event(
            entity_type="invoice",
            entity_id=invoice.id,
            action="created",
            actor_id=user_id,
            details={
                "invoice_number": invoice.invoice_number,
                "customer_id": invoice.customer_id,
                "total_amount": float(invoice.total_amount),
                "status": invoice.status
            }
        )

        db.session.commit()
        return invoice

    @classmethod
    def generate_recurring_invoices(
        cls,
        target_date: Optional[date] = None,
        subscription_id: Optional[int] = None,
        dry_run: bool = False,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if not target_date:
            target_date = datetime.now(timezone.utc).date()

        query = Subscription.query.filter(Subscription.status == "active")

        if subscription_id:
            query = query.filter(Subscription.id == subscription_id)
        else:
            query = query.filter(Subscription.next_billing_date <= target_date)

        subscriptions = query.all()

        results = {
            "target_date": target_date.isoformat(),
            "total_due_subscriptions": len(subscriptions),
            "generated_invoices": [],
            "skipped": [],
            "errors": []
        }

        for sub in subscriptions:
            if not sub.next_billing_date:
                results["skipped"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "reason": "Missing next_billing_date"
                })
                continue

            if sub.end_date and sub.next_billing_date > sub.end_date:
                results["skipped"].append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "reason": f"Next billing date exceeds subscription end date {sub.end_date.isoformat()}"
                })
                continue

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


def get_subscriptions_due_for_billing(as_of_date: date = None) -> list[Subscription]:
    """
    Return active subscriptions whose next_billing_date <= as_of_date.
    """
    as_of_date = as_of_date or date.today()
    return (
        Subscription.query
        .filter(
            Subscription.status == "active",
            Subscription.next_billing_date <= as_of_date,
        )
        .all()
    )


def run_billing_cycle(as_of_date: date = None) -> dict:
    """
    Process all subscriptions due for billing as of as_of_date.
    """
    as_of_date = as_of_date or date.today()
    due_subs = get_subscriptions_due_for_billing(as_of_date)

    processed = 0
    invoices_created = 0
    already_billed = 0
    errors = []

    for sub in due_subs:
        processed += 1
        try:
            invoice, err = create_invoice_from_subscription(sub, as_of_date)

            if err:
                errors.append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "error": str(err),
                })
                continue

            if invoice and invoice.subscription_id == sub.id:
                existing_for_period = sum(
                    1 for inv in sub.invoices
                    if inv.billing_period_start == sub.current_period_start
                )
                if existing_for_period > 1:
                    already_billed += 1
                else:
                    invoices_created += 1

            plan = sub.plan
            new_start = sub.current_period_end
            new_end = _compute_period_end(
                new_start, plan.billing_interval, plan.billing_interval_count
            )
            sub.current_period_start = new_start
            sub.current_period_end = new_end
            sub.next_billing_date = new_end
            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            logger.exception(
                "Billing cycle error for subscription %s: %s",
                sub.subscription_number, exc
            )
            errors.append({
                "subscription_id": sub.id,
                "subscription_number": sub.subscription_number,
                "error": str(exc),
            })

    return {
        "as_of_date": as_of_date.isoformat(),
        "processed": processed,
        "invoices_created": invoices_created,
        "already_billed": already_billed,
        "errors": errors,
    }