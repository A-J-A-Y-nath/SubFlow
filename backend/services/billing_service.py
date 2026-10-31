"""
Billing Service — SubFlow Member 3
Recurring billing engine: identifies due subscriptions and generates invoices.
Designed to be idempotent — safe to call multiple times for the same period.
"""
from datetime import date
import logging

from backend.extensions import db
from backend.models.subscription import Subscription
from backend.services.invoice_service import create_invoice_from_subscription
from backend.services.subscription_service import _compute_period_end

logger = logging.getLogger(__name__)


def get_subscriptions_due_for_billing(as_of_date: date = None) -> list[Subscription]:
    """
    Return active subscriptions whose next_billing_date <= as_of_date.
    """
    as_of_date = as_of_date or date.today()
    return (
        Subscription.query
        .filter(
            Subscription.status == "active",
            Subscription.next_billing_date <= as_of_date,
        )
        .all()
    )


def run_billing_cycle(as_of_date: date = None) -> dict:
    """
    Process all subscriptions due for billing as of as_of_date.

    For each due subscription:
      1. Attempt to generate an invoice (idempotent — unique constraint prevents duplicates).
      2. Advance next_billing_date to the next period.
      3. Log failures per subscription; one failure does not stop others.

    Returns a summary dict:
      { processed, invoices_created, already_billed, errors }
    """
    as_of_date = as_of_date or date.today()
    due_subs = get_subscriptions_due_for_billing(as_of_date)

    processed = 0
    invoices_created = 0
    already_billed = 0
    errors = []

    for sub in due_subs:
        processed += 1
        try:
            invoice, err = create_invoice_from_subscription(sub, as_of_date)

            if err:
                errors.append({
                    "subscription_id": sub.id,
                    "subscription_number": sub.subscription_number,
                    "error": str(err),
                })
                continue

            # Detect whether this was a duplicate (invoice already existed)
            if invoice and invoice.subscription_id == sub.id:
                # Check if invoice was just created (no id mismatch)
                # We determine "already billed" by checking if billing_period_start
                # matches current period (the service returns existing on duplicate)
                existing_for_period = sum(
                    1 for inv in sub.invoices
                    if inv.billing_period_start == sub.current_period_start
                )
                if existing_for_period > 1:
                    already_billed += 1
                else:
                    invoices_created += 1

            # Advance billing period regardless (idempotent advance)
            plan = sub.plan
            new_start = sub.current_period_end
            new_end = _compute_period_end(
                new_start, plan.billing_interval, plan.billing_interval_count
            )
            sub.current_period_start = new_start
            sub.current_period_end = new_end
            sub.next_billing_date = new_end
            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            logger.exception(
                "Billing cycle error for subscription %s: %s",
                sub.subscription_number, exc
            )
            errors.append({
                "subscription_id": sub.id,
                "subscription_number": sub.subscription_number,
                "error": str(exc),
            })

    return {
        "as_of_date": as_of_date.isoformat(),
        "processed": processed,
        "invoices_created": invoices_created,
        "already_billed": already_billed,
        "errors": errors,
    }
