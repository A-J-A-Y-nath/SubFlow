# SubFlow Financial Analytics & Reporting Engine

## 1. Overview
The **Analytics and Reports** module provides real-time financial metrics, receivables aging analysis, revenue timeline series, and subscription distribution formatted for interactive **Recharts** visualizations.

---

## 2. Key Performance Indicators (KPIs)

- **Total Recorded Revenue:** Sum of `Payment.amount` where `status == 'completed'`. Excludes failed and pending payments.
- **Estimated MRR:** Sum of `Subscription.recurring_amount` for active subscriptions.
- **Total Invoiced:** Sum of `Invoice.total_amount` for uncancelled statements.
- **Outstanding Balance:** Sum of `Invoice.balance_due` where `status in ('posted', 'partial')` and `balance_due > 0`.
- **Overdue Balance:** Sum of `Invoice.balance_due` where `(status == 'overdue' or (status in ('posted', 'partial') and due_date < today))` and `balance_due > 0`.
- **Collection Efficiency (%):**
  $$\text{Collection Rate} = \min\left(100.0, \frac{\text{Total Recorded Revenue}}{\text{Total Invoiced}} \times 100\right)$$

---

## 3. Receivables Aging Buckets

Outstanding balances are grouped based on calendar days past `due_date`:
1. **Current (Not Due):** Invoices whose `due_date >= today`.
2. **1–30 Days Overdue:** $1 \le (\text{today} - \text{due\_date}) \le 30$.
3. **31–60 Days Overdue:** $31 \le (\text{today} - \text{due\_date}) \le 60$.
4. **61–90 Days Overdue:** $61 \le (\text{today} - \text{due\_date}) \le 90$.
5. **Over 90 Days Overdue:** $(\text{today} - \text{due\_date}) > 90$.

---

## 4. Recharts Visualization Endpoints

```http
GET /api/v1/reports/analytics?range=30d
Authorization: Bearer <token>
```

Response payload structure:
```json
{
  "success": true,
  "data": {
    "range": "30d",
    "mrr_estimate": 14250.00,
    "financial_summary": { ... },
    "revenue_trends": [
      { "date": "Oct 28", "key": "2026-10-28", "revenue": 1250.00, "transactions": 3 },
      { "date": "Oct 29", "key": "2026-10-29", "revenue": 3400.00, "transactions": 5 }
    ],
    "plan_distribution": [
      { "plan": "Professional Plan", "subscriptions": 12 },
      { "plan": "Enterprise Annual", "subscriptions": 4 }
    ],
    "invoice_status_breakdown": [
      { "status": "posted", "label": "Issued", "count": 14, "total_amount": 4200.00 },
      { "status": "paid", "label": "Paid", "count": 28, "total_amount": 9800.00 }
    ],
    "payment_methods": [
      { "method": "credit_card", "label": "Credit Card", "count": 22, "total_amount": 7600.00 },
      { "method": "bank_transfer", "label": "Bank Transfer", "count": 6, "total_amount": 2200.00 }
    ],
    "aging_report": { ... }
  }
}
```
