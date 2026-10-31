from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
from sqlalchemy import func
from backend.extensions import db
from backend.models.payment import Payment, PaymentAllocation
from backend.models.invoice import Invoice
from backend.models.customer import Customer
from backend.models.audit_log import AuditLog
from backend.services.discount_service import to_decimal

TWO_PLACES = Decimal("0.01")
ALLOWED_METHODS = ("credit_card", "bank_transfer", "stripe", "cash", "other")
ALLOWED_STATUSES = ("pending", "completed", "failed", "refunded")


class PaymentService:
    @staticmethod
    def generate_payment_number() -> str:
        """
        Generates unique, sequential payment receipt number: PAY-YYYY-XXXX.
        """
        current_year = datetime.now(timezone.utc).year
        prefix = f"PAY-{current_year}-"

        latest = (
            db.session.query(Payment.payment_number)
            .filter(Payment.payment_number.like(f"{prefix}%"))
            .order_by(Payment.id.desc())
            .first()
        )

        next_seq = 1
        if latest and latest[0]:
            try:
                seq_str = latest[0].replace(prefix, "")
                next_seq = int(seq_str) + 1
            except (ValueError, TypeError):
                next_seq = Payment.query.count() + 1

        payment_number = f"{prefix}{next_seq:04d}"
        while Payment.query.filter_by(payment_number=payment_number).first() is not None:
            next_seq += 1
            payment_number = f"{prefix}{next_seq:04d}"

        return payment_number

    @classmethod
    def record_payment(
        cls,
        customer_id: int,
        amount: Decimal | float | int,
        payment_method: str = "credit_card",
        status: str = "completed",
        payment_date: Optional[datetime] = None,
        transaction_reference: Optional[str] = None,
        invoice_id: Optional[int] = None,
        notes: Optional[str] = None,
        currency: str = "USD",
        user_id: Optional[int] = None
    ) -> Payment:
        """
        Records customer payment receipt and optionally allocates to target invoice.
        """
        customer = db.session.get(Customer, customer_id)
        if not customer:
            raise ValueError(f"Customer ID {customer_id} not found")

        amount_dec = to_decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if amount_dec <= Decimal("0.00"):
            raise ValueError("Payment amount must be greater than zero")

        method_clean = (payment_method or "credit_card").lower().strip()
        if method_clean not in ALLOWED_METHODS:
            raise ValueError(f"Invalid payment method. Allowed: {', '.join(ALLOWED_METHODS)}")

        status_clean = (status or "completed").lower().strip()
        if status_clean not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid payment status. Allowed: {', '.join(ALLOWED_STATUSES)}")

        # Validate unique transaction reference if provided
        if transaction_reference and transaction_reference.strip():
            ref_clean = transaction_reference.strip()
            existing_ref = Payment.query.filter_by(transaction_reference=ref_clean).first()
            if existing_ref:
                raise ValueError(f"Transaction reference '{ref_clean}' has already been recorded")
        else:
            ref_clean = None

        target_invoice = None
        if invoice_id:
            target_invoice = db.session.get(Invoice, invoice_id)
            if not target_invoice:
                raise ValueError(f"Target invoice ID {invoice_id} not found")
            if target_invoice.customer_id != customer.id:
                raise ValueError(f"Invoice {target_invoice.invoice_number} does not belong to customer {customer.company_name}")

        pay_num = cls.generate_payment_number()
        p_date = payment_date or datetime.now(timezone.utc)

        payment = Payment(
            payment_number=pay_num,
            customer_id=customer.id,
            invoice_id=target_invoice.id if target_invoice else None,
            amount=amount_dec,
            currency=currency or customer.currency or "USD",
            payment_method=method_clean,
            status=status_clean,
            transaction_reference=ref_clean,
            payment_date=p_date,
            notes=notes
        )
        db.session.add(payment)
        db.session.flush()

        # If completed payment and target invoice specified, allocate immediately
        if status_clean == "completed" and target_invoice:
            allocation_amount = min(amount_dec, to_decimal(target_invoice.balance_due))
            if allocation_amount > Decimal("0.00"):
                allocation = PaymentAllocation(
                    payment_id=payment.id,
                    invoice_id=target_invoice.id,
                    amount_allocated=allocation_amount
                )
                db.session.add(allocation)
                db.session.flush()
                cls.reconcile_invoice(target_invoice)

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action="PAYMENT_RECORDED",
            entity_type="Payment",
            entity_id=str(payment.id),
            new_values={
                "payment_number": payment.payment_number,
                "customer_id": payment.customer_id,
                "amount": float(payment.amount),
                "status": payment.status,
                "payment_method": payment.payment_method
            }
        )
        db.session.add(audit)
        return payment

    @classmethod
    def allocate_payment(
        cls,
        payment_id: int,
        allocations: List[Dict[str, Any]],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Allocates unallocated completed payment balance across one or more customer invoices.
        """
        payment = db.session.get(Payment, payment_id)
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} does not exist")

        if payment.status != "completed":
            raise ValueError(f"Only completed payments can be allocated (current status: '{payment.status}')")

        if not allocations or len(allocations) == 0:
            raise ValueError("No allocation items provided")

        # Current total allocated
        existing_allocated = (
            db.session.query(func.coalesce(func.sum(PaymentAllocation.amount_allocated), 0))
            .filter(PaymentAllocation.payment_id == payment.id)
            .scalar()
        )
        existing_allocated_dec = to_decimal(existing_allocated).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        payment_amount_dec = to_decimal(payment.amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        available_balance = max(Decimal("0.00"), payment_amount_dec - existing_allocated_dec)

        # Total requested new allocation
        total_requested = Decimal("0.00")
        validated_items = []

        for item in allocations:
            inv_id = item.get("invoice_id")
            alloc_amt = to_decimal(item.get("amount", 0)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            if alloc_amt <= Decimal("0.00"):
                raise ValueError("Allocation amount must be greater than zero")

            invoice = db.session.get(Invoice, inv_id)
            if not invoice:
                raise ValueError(f"Invoice ID {inv_id} not found")

            if invoice.customer_id != payment.customer_id:
                raise ValueError(
                    f"Invoice {invoice.invoice_number} belongs to another customer. Cross-customer allocation is forbidden."
                )

            if invoice.status == "cancelled":
                raise ValueError(f"Cannot allocate payment to cancelled invoice {invoice.invoice_number}")

            inv_balance = to_decimal(invoice.balance_due).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if alloc_amt > inv_balance:
                raise ValueError(
                    f"Allocation of {alloc_amt} exceeds invoice {invoice.invoice_number} balance due of {inv_balance}"
                )

            total_requested += alloc_amt
            validated_items.append((invoice, alloc_amt))

        if total_requested > available_balance:
            raise ValueError(
                f"Total requested allocation ({total_requested}) exceeds available payment balance ({available_balance})"
            )

        new_allocations = []
        for invoice, alloc_amt in validated_items:
            alloc = PaymentAllocation(
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount_allocated=alloc_amt
            )
            db.session.add(alloc)
            db.session.flush()
            cls.reconcile_invoice(invoice)
            new_allocations.append(alloc)

        # Audit log
        audit = AuditLog(
            user_id=user_id,
            action="PAYMENT_ALLOCATED",
            entity_type="Payment",
            entity_id=str(payment.id),
            new_values={
                "payment_number": payment.payment_number,
                "amount_allocated": float(total_requested),
                "invoices_affected": [inv.invoice_number for inv, _ in validated_items]
            }
        )
        db.session.add(audit)
        db.session.commit()

        remaining_unallocated = available_balance - total_requested
        return {
            "payment_id": payment.id,
            "payment_number": payment.payment_number,
            "total_allocated_now": float(total_requested),
            "remaining_unallocated": float(remaining_unallocated),
            "allocations": [a.to_dict() for a in new_allocations]
        }

    @staticmethod
    def reconcile_invoice(invoice: Invoice) -> Invoice:
        """
        Recalculates amount_paid and balance_due for an invoice based on actual PaymentAllocations,
        and synchronizes invoice status (paid, partial, posted).
        """
        total_paid = (
            db.session.query(func.coalesce(func.sum(PaymentAllocation.amount_allocated), 0))
            .filter(PaymentAllocation.invoice_id == invoice.id)
            .scalar()
        )
        total_paid_dec = to_decimal(total_paid).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        total_amount_dec = to_decimal(invoice.total_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        invoice.amount_paid = total_paid_dec
        invoice.balance_due = max(Decimal("0.00"), total_amount_dec - total_paid_dec)

        # Update status if not cancelled
        if invoice.status != "cancelled":
            if invoice.balance_due == Decimal("0.00") and total_amount_dec > Decimal("0.00"):
                invoice.status = "paid"
            elif invoice.amount_paid > Decimal("0.00"):
                invoice.status = "partial"
            elif invoice.status in ("paid", "partial") and invoice.amount_paid == Decimal("0.00"):
                invoice.status = "posted"

        return invoice

    @staticmethod
    def get_payment_summary(payment_id: int) -> Dict[str, Any]:
        """
        Returns full payment information including allocations and remaining unallocated balance.
        """
        payment = db.session.get(Payment, payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        total_allocated = (
            db.session.query(func.coalesce(func.sum(PaymentAllocation.amount_allocated), 0))
            .filter(PaymentAllocation.payment_id == payment.id)
            .scalar()
        )
        allocated_dec = to_decimal(total_allocated).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        payment_amount_dec = to_decimal(payment.amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        unallocated_dec = max(Decimal("0.00"), payment_amount_dec - allocated_dec)

        alloc_details = []
        for alloc in payment.allocations:
            alloc_details.append({
                "id": alloc.id,
                "invoice_id": alloc.invoice_id,
                "invoice_number": alloc.invoice.invoice_number if alloc.invoice else None,
                "invoice_total": float(alloc.invoice.total_amount) if alloc.invoice else 0.0,
                "amount_allocated": float(alloc.amount_allocated),
                "created_at": alloc.created_at.isoformat() if alloc.created_at else None
            })

        return {
            **payment.to_dict(),
            "allocated_amount": float(allocated_dec),
            "unallocated_amount": float(unallocated_dec),
            "allocations": alloc_details
        }
