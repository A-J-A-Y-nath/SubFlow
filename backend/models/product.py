from datetime import datetime, timezone
from decimal import Decimal
from backend.extensions import db


class Product(db.Model):
    """
    Product catalog model representing sellable recurring and non-recurring items.
    """
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    is_recurring = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    default_price = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(10), default="USD", nullable=False)
    unit_of_measure = db.Column(db.String(50), default="unit", nullable=False)  # 'seat', 'unit', 'user', 'month'

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    variants = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    quotation_lines = db.relationship("QuotationLine", back_populates="product")
    subscription_lines = db.relationship("SubscriptionLine", back_populates="product")
    invoice_lines = db.relationship("InvoiceLine", back_populates="product")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "description": self.description,
            "is_recurring": self.is_recurring,
            "is_active": self.is_active,
            "default_price": float(self.default_price) if self.default_price is not None else 0.0,
            "currency": self.currency,
            "unit_of_measure": self.unit_of_measure,
            "variants_count": len(self.variants) if self.variants else 0,
            "variants": [variant.to_dict() for variant in self.variants] if self.variants else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProductVariant(db.Model):
    """
    Product variant model for configurable options, additional pricing, and dimensions.
    """
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    attributes = db.Column(db.JSON, default=dict, nullable=False)  # e.g. {"description": "...", "tier": "pro"}
    price_extra = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    product = db.relationship("Product", back_populates="variants")

    def to_dict(self) -> dict:
        base_price_val = self.product.default_price if (self.product and self.product.default_price is not None) else 0.00
        price_extra_val = self.price_extra if self.price_extra is not None else 0.00
        base_dec = Decimal(str(base_price_val))
        extra_dec = Decimal(str(price_extra_val))
        final_dec = base_dec + extra_dec

        desc = ""
        if isinstance(self.attributes, dict):
            desc = self.attributes.get("description", "")

        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "sku": self.sku,
            "name": self.name,
            "description": desc,
            "attributes": self.attributes or {},
            "base_price": float(base_dec),
            "price_extra": float(extra_dec),
            "final_price": float(final_dec),
            "currency": self.product.currency if self.product else "USD",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
