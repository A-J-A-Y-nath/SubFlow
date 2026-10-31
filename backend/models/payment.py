from datetime import datetime, timezone
from backend.extensions import db


class Payment(db.Model):
    """
    Payment transaction model recording customer receipts across payment gateways.
    """
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True)
    
    amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    
    # 'credit_card', 'bank_transfer', 'stripe', 'cash', 'other'
    payment_method = db.Column(db.String(50), default="credit_card", nullable=False)
    
    # 'pending', 'completed', 'failed', 'refunded'
    status = db.Column(db.String(50), default="completed", nullable=False, index=True)
    transaction_reference = db.Column(db.String(255), nullable=True, index=True)
    payment_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = db.relationship("Customer", back_populates="payments")
    invoice = db.relationship("Invoice", back_populates="payments")
    allocations = db.relationship("PaymentAllocation", back_populates="payment", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_number": self.payment_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.company_name if self.customer else None,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice.invoice_number if self.invoice else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "status": self.status,
            "transaction_reference": self.transaction_reference,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None,
            "notes": self.notes,
            "allocations_count": len(self.allocations) if self.allocations else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentAllocation(db.Model):
    """
    Payment allocation model linking payments to specific invoice balances.
    """
    __tablename__ = "payment_allocations"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_allocated = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    payment = db.relationship("Payment", back_populates="allocations")
    invoice = db.relationship("Invoice", back_populates="payment_allocations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "invoice_id": self.invoice_id,
            "amount_allocated": float(self.amount_allocated) if self.amount_allocated is not None else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
