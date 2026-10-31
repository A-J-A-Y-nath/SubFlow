from datetime import datetime, timezone
from backend.extensions import db


class Subscription(db.Model):
    """
    Subscription lifecycle model managing billing periods, renewals, and recurring charges.
    """
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    subscription_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)
    
    # Status: 'draft', 'active', 'paused', 'cancelled', 'expired'
    status = db.Column(db.String(50), default="draft", nullable=False, index=True)
    
    # Billing schedule
    start_date = db.Column(db.Date, nullable=False)
    current_period_start = db.Column(db.Date, nullable=False)
    current_period_end = db.Column(db.Date, nullable=False)
    trial_end = db.Column(db.Date, nullable=True)
    next_billing_date = db.Column(db.Date, nullable=True, index=True)
    auto_renew = db.Column(db.Boolean, default=True, nullable=False)
    
    # Cancellation info
    cancelled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancel_reason = db.Column(db.Text, nullable=True)
    
    # Financials
    recurring_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = db.relationship("Customer", back_populates="subscriptions")
    plan = db.relationship("Plan", back_populates="subscriptions")
    quotation = db.relationship("Quotation", back_populates="subscriptions")
    lines = db.relationship("SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="subscription")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subscription_number": self.subscription_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.company_name if self.customer else None,
            "plan_id": self.plan_id,
            "plan_name": self.plan.name if self.plan else None,
            "quotation_id": self.quotation_id,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "auto_renew": self.auto_renew,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "cancel_reason": self.cancel_reason,
            "recurring_amount": float(self.recurring_amount) if self.recurring_amount is not None else 0.0,
            "currency": self.currency,
            "lines": [line.to_dict() for line in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SubscriptionLine(db.Model):
    """
    Line items attached to an active subscription (products, add-ons, seats).
    """
    __tablename__ = "subscription_lines"

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1.00, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    recurring_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)

    # Relationships
    subscription = db.relationship("Subscription", back_populates="lines")
    product = db.relationship("Product", back_populates="subscription_lines")
    variant = db.relationship("ProductVariant")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_variant_id": self.product_variant_id,
            "variant_name": self.variant.name if self.variant else None,
            "description": self.description,
            "quantity": float(self.quantity) if self.quantity is not None else 1.0,
            "unit_price": float(self.unit_price) if self.unit_price is not None else 0.0,
            "discount_percent": float(self.discount_percent) if self.discount_percent is not None else 0.0,
            "recurring_amount": float(self.recurring_amount) if self.recurring_amount is not None else 0.0,
        }
