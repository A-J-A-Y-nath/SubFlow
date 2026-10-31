from datetime import datetime, timezone
from backend.extensions import db


class Quotation(db.Model):
    """
    Quotation model representing subscription proposals sent to customers.
    """
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Status: 'draft', 'sent', 'approved', 'rejected', 'expired'
    status = db.Column(db.String(50), default="draft", nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=False)
    valid_until = db.Column(db.Date, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    
    # Financial summary
    subtotal = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    
    terms_and_conditions = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = db.relationship("Customer", back_populates="quotations")
    plan = db.relationship("Plan", back_populates="quotations")
    creator = db.relationship("User", foreign_keys=[created_by_id], back_populates="created_quotations")
    lines = db.relationship("QuotationLine", back_populates="quotation", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", back_populates="quotation")
    invoices = db.relationship("Invoice", back_populates="quotation")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "quotation_number": self.quotation_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer.company_name if self.customer else None,
            "plan_id": self.plan_id,
            "plan_name": self.plan.name if self.plan else None,
            "created_by_id": self.created_by_id,
            "creator_name": self.creator.full_name if self.creator else None,
            "status": self.status,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "currency": self.currency,
            "subtotal": float(self.subtotal) if self.subtotal is not None else 0.0,
            "discount_amount": float(self.discount_amount) if self.discount_amount is not None else 0.0,
            "tax_amount": float(self.tax_amount) if self.tax_amount is not None else 0.0,
            "total_amount": float(self.total_amount) if self.total_amount is not None else 0.0,
            "terms_and_conditions": self.terms_and_conditions,
            "notes": self.notes,
            "lines": [line.to_dict() for line in self.lines] if self.lines else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QuotationLine(db.Model):
    """
    Individual line items associated with a quotation.
    """
    __tablename__ = "quotation_lines"

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1.00, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)

    # Relationships
    quotation = db.relationship("Quotation", back_populates="lines")
    product = db.relationship("Product", back_populates="quotation_lines")
    variant = db.relationship("ProductVariant")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "quotation_id": self.quotation_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "product_variant_id": self.product_variant_id,
            "variant_name": self.variant.name if self.variant else None,
            "description": self.description,
            "quantity": float(self.quantity) if self.quantity is not None else 1.0,
            "unit_price": float(self.unit_price) if self.unit_price is not None else 0.0,
            "discount_percent": float(self.discount_percent) if self.discount_percent is not None else 0.0,
            "total_amount": float(self.total_amount) if self.total_amount is not None else 0.0,
        }
