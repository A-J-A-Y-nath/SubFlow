# SubFlow Discount Rules Engine

## 1. Overview
The **Discount Rules** module evaluates promotional coupons, campaigns, minimum order qualifications, percentage ceilings, and usage allowances.

---

## 2. Discount Types & Calculations

### 2.1 Percentage Discounts (`percentage`)
- Value between `0.01` and `100.00`.
- Calculation: $\text{discount} = \text{order\_amount} \times (\text{value} / 100)$.
- If `max_discount_amount` is set, capped at $\min(\text{discount}, \text{max\_discount\_amount})$.

### 2.2 Fixed Discounts (`fixed`)
- Value $> 0.00$.
- Deducts exact fixed dollar amount.
- Capped at `order_amount` so invoice totals never drop below zero.

---

## 3. Validation Criteria

Before applying a coupon code:
1. **Active Status:** `is_active == True`.
2. **Campaign Schedule:** Current UTC time within `[valid_from, valid_to]`.
3. **Usage Threshold:** `max_uses is None` or `current_uses < max_uses`.
4. **Order Qualification:** `order_amount >= min_order_amount`.
5. **Plan Restrictions:** If `applicable_plans` is non-empty, the subscription plan code must match.

---

## 4. Endpoints Reference

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/discounts` | Admin, Staff, Customer | List rules with search and active status filter. |
| `POST` | `/api/v1/discounts` | Admin, Staff | Create promotional campaign rule. |
| `GET` | `/api/v1/discounts/<id>` | Admin, Staff, Customer | Discount rule configuration. |
| `PUT` | `/api/v1/discounts/<id>` | Admin, Staff | Update discount rule properties. |
| `POST` | `/api/v1/discounts/<id>/toggle-status` | Admin, Staff | Toggle active/inactive flag. |
| `GET` | `/api/v1/discounts/validate/<code>` | Admin, Staff, Customer | Live validation check with `?amount=` and `?plan_code=`. |
