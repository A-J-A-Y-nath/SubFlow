from datetime import datetime, timezone
from backend.extensions import db


class Plan(db.Model):
    """
    Subscription plan model defining billing cadences, trial periods, and base pricing.
    """
    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)

    # Billing cadence
    billing_interval = db.Column(db.String(50), default="monthly", nullable=False)  # 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'
    billing_interval_count = db.Column(db.Integer, default=1, nullable=False)

    # Financials
    base_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    setup_fee = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)

    # Features & Policies
    trial_days = db.Column(db.Integer, default=0, nullable=False)
    features = db.Column(db.JSON, default=list, nullable=False)  # list of strings or dict with meta
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    subscriptions = db.relationship("Subscription", back_populates="plan")
    quotations = db.relationship("Quotation", back_populates="plan")

    def to_dict(self) -> dict:
        features_list = []
        meta = {}
        if isinstance(self.features, list):
            features_list = self.features
        elif isinstance(self.features, dict):
            features_list = self.features.get("bullets", [])
            meta = self.features

        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "billing_interval": self.billing_interval,
            "billing_interval_count": self.billing_interval_count,
            "base_price": float(self.base_price) if self.base_price is not None else 0.0,
            "setup_fee": float(self.setup_fee) if self.setup_fee is not None else 0.0,
            "currency": self.currency,
            "trial_days": self.trial_days,
            "features": features_list,
            "min_quantity": meta.get("min_quantity", 1),
            "available_from": meta.get("available_from", None),
            "available_until": meta.get("available_until", None),
            "auto_renew": meta.get("auto_renew", True),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
