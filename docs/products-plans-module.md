# SubFlow — Product, Variant & Subscription Plan Management Module

This documentation summarizes the implementation of the **Product Management**, **Product Variant Management**, and **Subscription Plan Management** modules completed for SubFlow on branch `feature/products-plans`.

---

## 1. Module Overview

This module provides enterprise-ready catalog and plan management capabilities, fully adhering to SubFlow's common architecture:
- **Role-Based Access Control (RBAC):** Admin and Staff have full management permissions (create, read, update, deactivate, delete); Customers have read-only access restricted to active products and currently available plans.
- **Monetary Precision:** Implemented using PostgreSQL `NUMERIC(12, 2)` and Python `Decimal` arithmetic to eliminate floating-point rounding errors.
- **Real-Time Variant Pricing Formula:**
  $$\text{Final Unit Price} = \text{Base Product Price} + \text{Variant Additional Price}$$
- **Lifecycle & Deletion Guards:** Records cannot be deleted if associated with active subscriptions, quotations, or invoices; users are advised to deactivate them instead.
- **Audit Logging:** All mutations (creations, updates, status toggles, deletions) log audit records into `audit_logs`.

---

## 2. API Endpoints Specification

All endpoints use standard URL prefix `/api/v1` and require `Authorization: Bearer <token>`.

### 2.1 Product Catalog Endpoints (`/api/v1/products`)

| Endpoint | Method | Allowed Roles | Description |
| :--- | :---: | :--- | :--- |
| `/products` | `GET` | Admin, Staff, Customer | List products with pagination, search filter (`name` or `sku`), type filter (`is_recurring`), and status filter (`is_active`). Customers only receive active products. |
| `/products` | `POST` | Admin, Staff | Create a new product. Validates required fields, non-negative price, and SKU uniqueness. Supports initial variant creation. |
| `/products/<id>` | `GET` | Admin, Staff, Customer | Retrieve details for a specific product and its variants. Returns 404 for customers if deactivated. |
| `/products/<id>` | `PUT` | Admin, Staff | Update product properties (name, sku, default_price, unit_of_measure, description, is_recurring, is_active). |
| `/products/<id>/status` | `PATCH` | Admin, Staff | Toggle or explicitly set active/inactive status (`{"is_active": true/false}`). |
| `/products/<id>` | `DELETE` | Admin, Staff | Delete product if not referenced by quotation lines, subscription lines, or invoice lines (returns 409 `PRODUCT_IN_USE` otherwise). |

#### Product Payload Example:
```json
{
  "name": "Cloud Enterprise Storage",
  "sku": "PROD-STORAGE-ENT",
  "description": "High performance block storage tier",
  "default_price": 49.99,
  "currency": "USD",
  "unit_of_measure": "GB",
  "is_recurring": true,
  "is_active": true
}
```

---

### 2.2 Product Variant Endpoints (`/api/v1/products/<product_id>/variants`)

| Endpoint | Method | Allowed Roles | Description |
| :--- | :---: | :--- | :--- |
| `/products/<id>/variants` | `GET` | Admin, Staff, Customer | List all configurable variants for a product, returning base price, additional price, and computed final unit price. |
| `/products/<id>/variants` | `POST` | Admin, Staff | Create a variant with unique SKU, non-negative additional price, attributes, and optional description. |
| `/products/<id>/variants/<var_id>` | `GET` | Admin, Staff, Customer | Retrieve single variant details with price calculations. |
| `/products/<id>/variants/<var_id>` | `PUT` | Admin, Staff | Update variant name, SKU, price_extra, attributes, description, or status. |
| `/products/<id>/variants/<var_id>/status` | `PATCH` | Admin, Staff | Toggle or set variant active status. |
| `/products/<id>/variants/<var_id>` | `DELETE` | Admin, Staff | Delete variant if not referenced in quotation lines or subscription lines (returns 409 `VARIANT_IN_USE` otherwise). |

#### Variant Payload Example:
```json
{
  "name": "100GB Extra Capacity",
  "sku": "VAR-STORAGE-100GB",
  "price_extra": 25.00,
  "description": "Adds 100GB NVMe storage allocation",
  "is_active": true
}
```

#### Variant Response Example:
```json
{
  "id": 1,
  "product_id": 2,
  "product_name": "Cloud Enterprise Storage",
  "sku": "VAR-STORAGE-100GB",
  "name": "100GB Extra Capacity",
  "description": "Adds 100GB NVMe storage allocation",
  "base_price": 49.99,
  "price_extra": 25.00,
  "final_price": 74.99,
  "currency": "USD",
  "is_active": true
}
```

---

### 2.3 Subscription Plan Endpoints (`/api/v1/plans`)

| Endpoint | Method | Allowed Roles | Description |
| :--- | :---: | :--- | :--- |
| `/plans` | `GET` | Admin, Staff, Customer | List plans with pagination, cadence filter (`billing_interval`), status filter, and search. Customers are filtered by active status and date availability window. |
| `/plans` | `POST` | Admin, Staff | Create a subscription plan. Enforces unique plan code, valid billing interval, positive minimum quantity, non-negative prices, and valid date range (`available_until >= available_from`). |
| `/plans/<id>` | `GET` | Admin, Staff, Customer | Retrieve details for a specific plan. |
| `/plans/<id>` | `PUT` | Admin, Staff | Update plan pricing, cadence, features, min_quantity, or availability dates. |
| `/plans/<id>/status` | `PATCH` | Admin, Staff | Toggle or set plan active status (`{"is_active": true/false}`). |
| `/plans/<id>` | `DELETE` | Admin, Staff | Delete plan if not referenced in subscriptions or quotations (returns 409 `PLAN_IN_USE` otherwise). |

#### Plan Payload Example:
```json
{
  "name": "Professional Plan",
  "code": "PLAN-PRO-MO",
  "description": "Full-featured subscription for growing businesses",
  "billing_interval": "monthly",
  "billing_interval_count": 1,
  "base_price": 99.00,
  "setup_fee": 25.00,
  "currency": "USD",
  "trial_days": 14,
  "min_quantity": 1,
  "available_from": "2026-01-01",
  "available_until": "2026-12-31",
  "auto_renew": true,
  "is_active": true,
  "features": [
    "Up to 25 users",
    "Advanced Analytics",
    "Priority Support",
    "Unlimited Workspaces"
  ]
}
```

---

## 3. Frontend Pages & UI Capabilities

### 3.1 Products Page (`frontend/src/pages/ProductsPage.jsx`)
- **Product List Table:** Displays commercial name, SKU, recurring/one-off badge, formatted base unit price, unit of measure, variant count pill, status badge, creation date, and action buttons.
- **Search & Filters:** Real-time search by name or SKU, filter by type (All / Recurring / One-off), and filter by status (All / Active / Inactive).
- **Create & Edit Product Modal:** Validates non-negative price, SKU, required name, currency selection, unit of measure, and recurring toggle.
- **Variant Management Modal:** Interactive modal to inspect and manage variants for the selected product. Shows base price, allows adding/editing variants with additional price surcharge, and renders the calculated final unit price with instant arithmetic.
- **Confirmation Dialog:** Safe confirmation modal for deleting products or variants with clear warnings when in use.
- **Full State Handling:** Loading spinners, empty states with clear calls-to-action, success toasts, and error alerts.

### 3.2 Plans Page (`frontend/src/pages/PlansPage.jsx`)
- **Responsive Plan Cards Grid:** Card layout highlighting featured tiers, price with interval, one-time setup fee, free trial duration badge, minimum quantity badge, auto-renew badge, availability date range, and feature checklist.
- **Cadence Switcher:** Top filter tabs for All, Daily, Weekly, Monthly, Quarterly, and Yearly.
- **Create & Edit Plan Modal:** Full input form for name, code, billing interval, base price, setup fee, currency, trial days, minimum quantity, available from/until dates, features (one per line), auto-renew, and active status.
- **Destructive Deletion Guard Modal:** Confirmation dialog explaining deletion restrictions for plans with active subscriptions.
- **Full State Handling:** Loading spinners, empty states, success notifications, and inline validation messages.

---

## 4. Integration Notes for Teammates

1. **Member 3 (Subscriptions & Quotations):**
   - **Plan Selection:** Call `GET /api/v1/plans` to list active plans for subscription creation.
   - **Variant Selection in Lines:** When quoting or subscribing to a product variant, pass `product_id` and optional `product_variant_id`. Line unit price should equal `ProductVariant.final_price` or `Product.default_price`.
   - **Enforce Minimum Quantity:** Validate `quantity >= plan.min_quantity` before finalizing subscriptions.
2. **Member 4 (Invoices & Payments):**
   - Use `invoice_lines.product_id` and unit price based on the selected catalog product or variant price.
   - `Product.currency` and `Plan.currency` ensure multi-currency consistency across invoicing.

