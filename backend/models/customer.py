from datetime import datetime, timezone
from backend.extensions import db


class Customer(db.Model):
    """
    Customer entity representing companies or individuals subscribing to services.
    Can optionally be linked to a User account for self-service portal access.
    """
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True, index=True)
    company_name = db.Column(db.String(255), nullable=False, index=True)
    contact_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=True)
    
    # Billing Address
    billing_street = db.Column(db.String(255), nullable=True)
    billing_city = db.Column(db.String(100), nullable=True)
    billing_state = db.Column(db.String(100), nullable=True)
    billing_postal_code = db.Column(db.String(50), nullable=True)
    billing_country = db.Column(db.String(100), default="United States", nullable=False)
    
    # Financial and billing settings
    currency = db.Column(db.String(10), default="USD", nullable=False)
    vat_number = db.Column(db.String(50), nullable=True)
    payment_terms_days = db.Column(db.Integer, default=30, nullable=False)
    credit_limit = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user = db.relationship("User", back_populates="customer_profile")
    quotations = db.relationship("Quotation", back_populates="customer", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="customer", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "contact_name": self.contact_name,
            "email": self.email,
            "phone": self.phone,
            "billing_address": {
                "street": self.billing_street,
                "city": self.billing_city,
                "state": self.billing_state,
                "postal_code": self.billing_postal_code,
                "country": self.billing_country,
            },
            "currency": self.currency,
            "vat_number": self.vat_number,
            "payment_terms_days": self.payment_terms_days,
            "credit_limit": float(self.credit_limit) if self.credit_limit is not None else 0.0,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
