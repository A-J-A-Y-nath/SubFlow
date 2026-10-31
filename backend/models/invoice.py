from datetime import datetime, timezone
from backend.extensions import db


class Invoice(db.Model):
    """
    Invoice model for tracking recurring and one-off customer billings and receivables.
    billing_period_start + subscription_id form a unique key that prevents duplicate
    invoices being generated for the same subscription billing period.
    """
    __tablename__ = "invoices"
    __table_args__ = (
        db.UniqueConstraint(
            "subscription_id",
            "billing_period_start",
            name="uq_invoice_sub_period"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    
    # Status: 'draft', 'posted', 'paid', 'partial', 'overdue', 'cancelled'
    status = db.Column(db.String(50), default="draft", nullable=False, index=True)
    
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False, index=True)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    
    # Financials
    subtotal = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    amount_paid = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    balance_due = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    
    # Billing period this invoice covers (used for duplicate-billing prevention)
    billing_period_start = db.Column(db.Date, nullable=True, index=True)
    billing_period_end = db.Column(db.Date, nullable=True)

    notes = db.Column(db.Text, nullable=True)
    payment_terms = db.Column(db.String(100), default="Net 30", nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = db.relationship("Customer", back_populates="invoices")
    subscription = db.relationship("Subscription", back_populates="invoices")
    quotation = db.relationship("Quotation", back_populates="invoices")
    lines = db.relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="invoice")
    payment_allocations = db.relationship("PaymentAllocation", back_populates="invoice")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": (self.customer.company_name or self.customer.contact_name or self.customer.email) if self.customer else None,
            "subscription_id": self.subscription_id,
            "subscription_number": self.subscription.subscription_number if self.subscription else None,
            "quotation_id": self.quotation_id,
            "status": self.status,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "billing_period_start": self.billing_period_start.isoformat() if self.billing_period_start else None,
            "billing_period_end": self.billing_period_end.isoformat() if self.billing_period_end else None,
            "currency": self.currency,
            "subtotal": float(self.subtotal) if self.subtotal is not None else 0.0,
            "discount_amount": float(self.discount_amount) if self.discount_amount is not None else 0.0,
            "tax_amount": float(self.tax_amount) if self.tax_amount is not None else 0.0,
            "total_amount": float(self.total_amount) if self.total_amount is not None else 0.0,
            "amount_paid": float(self.amount_paid) if self.amount_paid is not None else 0.0,
            "balance_due": float(self.balance_due) if self.balance_due is not None else 0.0,
            "notes": self.notes,
            "payment_terms": self.payment_terms,
            "lines": [line.to_dict() for line in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoiceLine(db.Model):
    """
    Detailed items listed on an invoice.
    """
    __tablename__ = "invoice_lines"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1.00, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    line_total = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)

    # Relationships
    invoice = db.relationship("Invoice", back_populates="lines")
    product = db.relationship("Product", back_populates="invoice_lines")

    def __init__(self, **kwargs):
        if "amount" in kwargs and "line_total" not in kwargs:
            kwargs["line_total"] = kwargs.pop("amount")
        super().__init__(**kwargs)

    @property
    def amount(self):
        return self.line_total

    @amount.setter
    def amount(self, val):
        self.line_total = val

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "description": self.description,
            "quantity": float(self.quantity) if self.quantity is not None else 1.0,
            "unit_price": float(self.unit_price) if self.unit_price is not None else 0.0,
            "discount_percent": float(self.discount_percent) if self.discount_percent is not None else 0.0,
            "line_total": float(self.line_total) if self.line_total is not None else 0.0,
            "amount": float(self.line_total) if self.line_total is not None else 0.0,
        }
