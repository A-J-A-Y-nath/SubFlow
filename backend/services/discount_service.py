from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple, Optional
from backend.extensions import db
from backend.models.discount import DiscountRule

TWO_PLACES = Decimal("0.01")


def to_decimal(val) -> Decimal:
    """Helper to convert int, float, or str to Decimal safely."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


class DiscountService:
    @staticmethod
    def validate_and_calculate_discount(
        code: str,
        eligible_amount: Decimal | float | int = Decimal("0.00"),
        plan_code: Optional[str] = None
    ) -> Tuple[bool, Decimal, Optional[DiscountRule], Optional[str]]:
        """
        Validates coupon rules and returns:
        (is_valid, calculated_discount_amount, discount_rule, error_message)
        """
        if not code or not str(code).strip():
            return False, Decimal("0.00"), None, "Discount code cannot be empty"

        cleaned_code = str(code).strip().upper()
        rule = DiscountRule.query.filter_by(code=cleaned_code).first()

        if not rule:
            return False, Decimal("0.00"), None, f"Coupon code '{cleaned_code}' does not exist"

        if not rule.is_active:
            return False, Decimal("0.00"), rule, f"Coupon code '{cleaned_code}' is deactivated"

        now = datetime.now(timezone.utc)
        if rule.valid_from:
            valid_from = rule.valid_from if rule.valid_from.tzinfo else rule.valid_from.replace(tzinfo=timezone.utc)
            if now < valid_from:
                return False, Decimal("0.00"), rule, f"Coupon '{cleaned_code}' is not active yet (starts {valid_from.strftime('%Y-%m-%d')})"

        if rule.valid_to:
            valid_to = rule.valid_to if rule.valid_to.tzinfo else rule.valid_to.replace(tzinfo=timezone.utc)
            if now > valid_to:
                return False, Decimal("0.00"), rule, f"Coupon '{cleaned_code}' expired on {valid_to.strftime('%Y-%m-%d')}"

        if rule.max_uses is not None and rule.current_uses >= rule.max_uses:
            return False, Decimal("0.00"), rule, f"Coupon '{cleaned_code}' has reached its maximum redemption limit"

        order_amount_dec = to_decimal(eligible_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        min_order_dec = to_decimal(rule.min_order_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        if order_amount_dec < min_order_dec:
            return (
                False,
                Decimal("0.00"),
                rule,
                f"Minimum qualifying order amount for '{cleaned_code}' is {min_order_dec} (current: {order_amount_dec})"
            )

        # Plan restrictions
        if rule.applicable_plans and len(rule.applicable_plans) > 0:
            if not plan_code or plan_code not in rule.applicable_plans:
                return (
                    False,
                    Decimal("0.00"),
                    rule,
                    f"Coupon '{cleaned_code}' is only applicable to plans: {', '.join(rule.applicable_plans)}"
                )

        # Calculation
        rule_val_dec = to_decimal(rule.value)
        if rule.discount_type == "percentage":
            if rule_val_dec < Decimal("0.00") or rule_val_dec > Decimal("100.00"):
                return False, Decimal("0.00"), rule, "Invalid discount percentage configured"
            calc_discount = (order_amount_dec * (rule_val_dec / Decimal("100.00"))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if rule.max_discount_amount is not None:
                max_cap = to_decimal(rule.max_discount_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                if calc_discount > max_cap:
                    calc_discount = max_cap
        elif rule.discount_type == "fixed":
            if rule_val_dec < Decimal("0.00"):
                return False, Decimal("0.00"), rule, "Invalid fixed discount amount configured"
            calc_discount = rule_val_dec.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        else:
            return False, Decimal("0.00"), rule, f"Unsupported discount type '{rule.discount_type}'"

        # Capped so discount never exceeds order total
        final_discount = min(calc_discount, order_amount_dec)
        return True, final_discount, rule, None

    @staticmethod
    def record_usage(rule_id: int) -> bool:
        """
        Atomically increment current_uses for a discount rule.
        """
        rule = db.session.get(DiscountRule, rule_id)
        if not rule:
            return False
        if rule.max_uses is not None and rule.current_uses >= rule.max_uses:
            return False
        rule.current_uses = rule.current_uses + 1
        return True
