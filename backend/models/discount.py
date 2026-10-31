from datetime import datetime, timezone
from backend.extensions import db


class DiscountRule(db.Model):
    """
    Discount and promotion rules engine model supporting fixed/percentage discounts.
    """
    __tablename__ = "discount_rules"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # 'percentage' (e.g. 20.00 for 20%) or 'fixed' (e.g. 50.00 for $50 off)
    discount_type = db.Column(db.String(20), default="percentage", nullable=False)
    value = db.Column(db.Numeric(12, 2), nullable=False)
    
    min_order_amount = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    max_discount_amount = db.Column(db.Numeric(12, 2), nullable=True)
    
    valid_from = db.Column(db.DateTime(timezone=True), nullable=True)
    valid_to = db.Column(db.DateTime(timezone=True), nullable=True)
    
    max_uses = db.Column(db.Integer, nullable=True)
    current_uses = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Specific plans this coupon applies to (empty list = all plans)
    applicable_plans = db.Column(db.JSON, default=list, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def is_valid_now(self) -> bool:
        """Check if discount is currently active and within its validity window."""
        if not self.is_active:
            return False
        now = datetime.now(timezone.utc)
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        if self.max_uses is not None and self.current_uses >= self.max_uses:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "discount_type": self.discount_type,
            "value": float(self.value) if self.value is not None else 0.0,
            "min_order_amount": float(self.min_order_amount) if self.min_order_amount is not None else 0.0,
            "max_discount_amount": float(self.max_discount_amount) if self.max_discount_amount is not None else None,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "max_uses": self.max_uses,
            "current_uses": self.current_uses,
            "is_active": self.is_active,
            "is_valid": self.is_valid_now(),
            "applicable_plans": self.applicable_plans or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
