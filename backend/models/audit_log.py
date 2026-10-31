from datetime import datetime, timezone
from backend.extensions import db


class AuditLog(db.Model):
    """
    Immutable audit trail recording administrative and financial actions.
    """
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'SUBSCRIPTION_CREATED', 'INVOICE_PAID'
    entity_type = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'Subscription', 'Invoice'
    entity_id = db.Column(db.String(100), nullable=True)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    @classmethod
    def log_event(
        cls,
        entity_type: str,
        entity_id=None,
        action: str = "ACTION",
        actor_id=None,
        details=None,
        old_values=None,
        new_values=None,
        ip_address=None,
        user_agent=None
    ):
        try:
            entry = cls(
                user_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                new_values=details if details is not None else new_values,
                old_values=old_values,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(entry)
            return entry
        except Exception:
            return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user.email if self.user else None,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
