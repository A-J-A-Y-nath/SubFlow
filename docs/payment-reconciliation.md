# SubFlow Payment Processing & Reconciliation

## 1. Overview
The **Payments and Allocation** module manages payment transaction receipts, prevents duplicate transaction references, reconciles customer payments against invoice balances, and supports multi-invoice distribution.

---

## 2. Core Financial Data Models

- **Payment (`payments`):** Records money collected via `credit_card`, `bank_transfer`, `stripe`, `cash`, or `other`.
- **PaymentAllocation (`payment_allocations`):** Represents an exact dollar amount from a completed payment assigned to settle a specific invoice's `balance_due`.

---

## 3. Allocation and Reconciliation Rules

1. **Completed Funds Only:** Only payments with `status == 'completed'` can be allocated. Pending or failed transactions cannot be allocated.
2. **Customer Matching (Tenant Isolation):** A payment can only be allocated to invoices belonging to the exact same customer (`invoice.customer_id == payment.customer_id`). Cross-customer allocations trigger a 422 error.
3. **No Over-allocation:**
   - Total allocated from a payment cannot exceed `payment.amount`.
   - Allocation to an invoice cannot exceed `invoice.balance_due`.
4. **Reconciliation Formula:**
   $$\text{invoice.amount\_paid} = \sum \text{allocated amounts for this invoice}$$
   $$\text{invoice.balance\_due} = \max(0, \text{invoice.total\_amount} - \text{invoice.amount\_paid})$$
5. **Status Auto-Synchronization:**
   - If `balance_due == 0.00` and `total_amount > 0`: `status = 'paid'`
   - If `amount_paid > 0.00` and `balance_due > 0`: `status = 'partial'`
   - If `amount_paid == 0.00`: `status = 'posted'`

---

## 4. Multi-Invoice Payment Allocation

SubFlow supports receiving a single payment (e.g. wire transfer of $10,000) and allocating it across several outstanding invoices:

```http
POST /api/v1/payments/12/allocate
Authorization: Bearer <token>
Content-Type: application/json

{
  "allocations": [
    { "invoice_id": 4, "amount": 6000.00 },
    { "invoice_id": 7, "amount": 4000.00 }
  ]
}
```

Response:
```json
{
  "success": true,
  "message": "Payment successfully allocated",
  "data": {
    "payment_id": 12,
    "payment_number": "PAY-2026-0005",
    "total_allocated_now": 10000.00,
    "remaining_unallocated": 0.00,
    "allocations": [ ... ]
  }
}
```

---

## 5. Endpoints Reference

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/payments` | Admin, Staff, Customer | List payments with status, method, and customer filters. Customers see only own receipts. |
| `POST` | `/api/v1/payments` | Admin, Staff | Record payment receipt with optional instant allocation. |
| `GET` | `/api/v1/payments/<id>` | Admin, Staff, Customer | Detailed payment receipt with allocated amount, unallocated balance, and allocations. |
| `POST` | `/api/v1/payments/<id>/allocate` | Admin, Staff | Distribute available payment balance across customer invoices. |
| `GET` | `/api/v1/payments/invoice/<id>` | Admin, Staff, Customer | Payment allocation history for a specific invoice. |
