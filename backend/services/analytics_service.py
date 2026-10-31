from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import func, or_, and_, case
from backend.extensions import db
from backend.models.invoice import Invoice
from backend.models.payment import Payment
from backend.models.subscription import Subscription
from backend.models.plan import Plan


class AnalyticsService:
    @staticmethod
    def parse_date_range(range_filter: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        Parses date range keywords: '7d', '30d', 'month', 'year', 'all' into UTC datetime bounds.
        """
        now = datetime.now(timezone.utc)
        today = now.date()

        if range_filter == "7d":
            start = now - timedelta(days=7)
            return start, now
        elif range_filter == "30d":
            start = now - timedelta(days=30)
            return start, now
        elif range_filter == "month":
            start = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
            return start, now
        elif range_filter == "year":
            start = datetime(today.year, 1, 1, tzinfo=timezone.utc)
            return start, now
        return None, None

    @classmethod
    def get_financial_summary(
        cls,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculates core financial metrics from verified database transactions.
        """
        today = date.today()

        # 1. Total Recorded Revenue (completed payments)
        pay_query = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
            func.count(Payment.id).label("count")
        ).filter(Payment.status == "completed")

        if customer_id:
            pay_query = pay_query.filter(Payment.customer_id == customer_id)
        if start_date:
            pay_query = pay_query.filter(Payment.payment_date >= start_date)
        if end_date:
            pay_query = pay_query.filter(Payment.payment_date <= end_date)

        rev_res = pay_query.first()
        total_revenue = float(rev_res.revenue) if rev_res else 0.0
        completed_payments_count = rev_res.count if rev_res else 0

        # 2. Total Invoiced Amount (excluding cancelled)
        inv_query = db.session.query(
            func.coalesce(func.sum(Invoice.total_amount), 0).label("invoiced"),
            func.count(Invoice.id).label("count")
        ).filter(Invoice.status != "cancelled")

        if customer_id:
            inv_query = inv_query.filter(Invoice.customer_id == customer_id)
        if start_date:
            inv_query = inv_query.filter(Invoice.created_at >= start_date)
        if end_date:
            inv_query = inv_query.filter(Invoice.created_at <= end_date)

        inv_res = inv_query.first()
        total_invoiced = float(inv_res.invoiced) if inv_res else 0.0
        total_invoices_count = inv_res.count if inv_res else 0

        # 3. Outstanding Invoices (posted or partial with positive balance)
        out_query = db.session.query(
            func.coalesce(func.sum(Invoice.balance_due), 0).label("balance"),
            func.count(Invoice.id).label("count")
        ).filter(
            Invoice.status.in_(["posted", "partial"]),
            Invoice.balance_due > 0
        )
        if customer_id:
            out_query = out_query.filter(Invoice.customer_id == customer_id)

        out_res = out_query.first()
        outstanding_amount = float(out_res.balance) if out_res else 0.0
        outstanding_count = out_res.count if out_res else 0

        # 4. Overdue Invoices
        overdue_filter = or_(
            Invoice.status == "overdue",
            and_(
                Invoice.status.in_(["posted", "partial"]),
                Invoice.due_date < today,
                Invoice.balance_due > 0
            )
        )
        over_query = db.session.query(
            func.coalesce(func.sum(Invoice.balance_due), 0).label("balance"),
            func.count(Invoice.id).label("count")
        ).filter(overdue_filter)

        if customer_id:
            over_query = over_query.filter(Invoice.customer_id == customer_id)

        over_res = over_query.first()
        overdue_amount = float(over_res.balance) if over_res else 0.0
        overdue_count = over_res.count if over_res else 0

        # 5. Active Subscriptions count
        sub_query = Subscription.query.filter_by(status="active")
        if customer_id:
            sub_query = sub_query.filter_by(customer_id=customer_id)
        active_subscriptions_count = sub_query.count()

        # 6. Collection Rate
        collection_rate = (
            round((total_revenue / total_invoiced) * 100, 1)
            if total_invoiced > 0
            else (100.0 if total_revenue > 0 else 0.0)
        )

        return {
            "total_revenue": total_revenue,
            "total_invoiced": total_invoiced,
            "outstanding_amount": outstanding_amount,
            "outstanding_count": outstanding_count,
            "overdue_amount": overdue_amount,
            "overdue_count": overdue_count,
            "total_invoices_count": total_invoices_count,
            "completed_payments_count": completed_payments_count,
            "active_subscriptions_count": active_subscriptions_count,
            "collection_rate_percent": min(100.0, collection_rate),
            "currency": "USD"
        }

    @classmethod
    def get_revenue_trends(
        cls,
        period: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        customer_id: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """
        Computes revenue timeline formatted for Recharts.
        """
        query = Payment.query.filter(Payment.status == "completed")
        if customer_id:
            query = query.filter(Payment.customer_id == customer_id)
        if start_date:
            query = query.filter(Payment.payment_date >= start_date)
        if end_date:
            query = query.filter(Payment.payment_date <= end_date)

        payments = query.order_by(Payment.payment_date.asc()).all()

        grouped: Dict[str, Dict[str, Any]] = {}
        for p in payments:
            if not p.payment_date:
                continue
            if period == "daily":
                key = p.payment_date.strftime("%Y-%m-%d")
                label = p.payment_date.strftime("%b %d")
            else:
                key = p.payment_date.strftime("%Y-%m")
                label = p.payment_date.strftime("%b %Y")

            if key not in grouped:
                grouped[key] = {"date": label, "key": key, "revenue": 0.0, "transactions": 0}

            grouped[key]["revenue"] += float(p.amount)
            grouped[key]["transactions"] += 1

        trends = list(grouped.values())
        for item in trends:
            item["revenue"] = round(item["revenue"], 2)

        return trends

    @classmethod
    def get_invoice_status_breakdown(cls, customer_id: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Invoice breakdown counts and totals grouped by status.
        """
        query = db.session.query(
            Invoice.status,
            func.count(Invoice.id).label("count"),
            func.coalesce(func.sum(Invoice.total_amount), 0).label("total")
        )
        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)

        rows = query.group_by(Invoice.status).all()
        status_map = {
            "draft": "Draft",
            "posted": "Issued",
            "partial": "Partially Paid",
            "paid": "Paid",
            "overdue": "Overdue",
            "cancelled": "Cancelled"
        }

        result = []
        for status_val, count, total in rows:
            result.append({
                "status": status_val,
                "label": status_map.get(status_val, status_val.title()),
                "count": count,
                "total_amount": round(float(total), 2)
            })

        return result

    @classmethod
    def get_payment_method_breakdown(cls, customer_id: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Distribution of completed payments by payment method.
        """
        query = db.session.query(
            Payment.payment_method,
            func.count(Payment.id).label("count"),
            func.coalesce(func.sum(Payment.amount), 0).label("total")
        ).filter(Payment.status == "completed")

        if customer_id:
            query = query.filter(Payment.customer_id == customer_id)

        rows = query.group_by(Payment.payment_method).all()
        method_labels = {
            "credit_card": "Credit Card",
            "bank_transfer": "Bank Transfer",
            "stripe": "Stripe Gateway",
            "cash": "Cash / Manual",
            "other": "Other"
        }

        result = []
        for method, count, total in rows:
            result.append({
                "method": method,
                "label": method_labels.get(method, method.replace("_", " ").title()),
                "count": count,
                "total_amount": round(float(total), 2)
            })

        return result

    @classmethod
    def get_aging_report(cls, customer_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Accounts receivables aging analysis (1-30, 31-60, 61-90, 90+ days past due).
        """
        today = date.today()
        query = Invoice.query.filter(
            Invoice.status.in_(["posted", "partial", "overdue"]),
            Invoice.balance_due > 0
        )
        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)

        invoices = query.all()

        aging = {
            "current": {"label": "Current (Not Due)", "amount": 0.0, "count": 0},
            "1_30": {"label": "1–30 Days", "amount": 0.0, "count": 0},
            "31_60": {"label": "31–60 Days", "amount": 0.0, "count": 0},
            "61_90": {"label": "61–90 Days", "amount": 0.0, "count": 0},
            "over_90": {"label": "Over 90 Days", "amount": 0.0, "count": 0},
        }

        for inv in invoices:
            bal = float(inv.balance_due)
            if not inv.due_date or inv.due_date >= today:
                aging["current"]["amount"] += bal
                aging["current"]["count"] += 1
            else:
                days_overdue = (today - inv.due_date).days
                if days_overdue <= 30:
                    aging["1_30"]["amount"] += bal
                    aging["1_30"]["count"] += 1
                elif days_overdue <= 60:
                    aging["31_60"]["amount"] += bal
                    aging["31_60"]["count"] += 1
                elif days_overdue <= 90:
                    aging["61_90"]["amount"] += bal
                    aging["61_90"]["count"] += 1
                else:
                    aging["over_90"]["amount"] += bal
                    aging["over_90"]["count"] += 1

        for k in aging:
            aging[k]["amount"] = round(aging[k]["amount"], 2)

        return aging
