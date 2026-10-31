# SubFlow API Contracts & Developer Integration Guide

This document establishes the official API contracts, conventions, and module blueprints for **SubFlow**. All three feature developers must adhere to these specifications to ensure clean integration without merge conflicts.

---

## 1. Global API Conventions

### 1.1 Base URL & Prefix
All endpoints are namespaced under the versioned prefix:
```http
/api/v1
```

### 1.2 Authentication Headers
Authenticated endpoints require a standard Bearer JWT token header:
```http
Authorization: Bearer <access_token>
```

### 1.3 Standard Response Envelopes

#### Success Response Envelope (HTTP 200, 201)
```json
{
  "success": true,
  "message": "Human-readable description of the operation",
  "data": { ... },
  "meta": { ... } // Optional metadata
}
```

#### Paginated List Response Envelope (HTTP 200)
```json
{
  "success": true,
  "message": "Items retrieved successfully",
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total_items": 45,
      "total_pages": 3,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

#### Error Response Envelope (HTTP 4xx, 5xx)
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_ENUM",
    "message": "A clear, actionable explanation of the error",
    "details": null // Optional list of field validation errors or dict
  }
}
```

### 1.4 Standard HTTP Status Codes

| Status Code | Meaning | When to Use |
| :--- | :--- | :--- |
| `200 OK` | Request succeeded | Successful GET, PUT, PATCH requests |
| `201 Created` | Resource created | Successful POST record creations |
| `400 Bad Request` | Malformed payload | Missing required fields, syntax error |
| `401 Unauthorized` | Missing / invalid token | Expired token, unauthenticated caller |
| `403 Forbidden` | Insufficient permissions | Caller role not allowed (e.g. non-admin creating staff) |
| `404 Not Found` | Resource not found | Record with specified ID does not exist |
| `409 Conflict` | Unique conflict | Email or SKU already registered |
| `422 Unprocessable`| Validation failed | Password fails complexity, invalid date range |
| `500 Server Error` | Unexpected failure | Uncaught exception (logged to server) |

---

## 2. Authentication & RBAC Contracts

### 2.1 Role Matrix

| Endpoint | Method | Admin | Staff | Customer | Anonymous |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `/auth/register` | `POST` | ✓ | ✓ | ✓ | ✓ |
| `/auth/login` | `POST` | ✓ | ✓ | ✓ | ✓ |
| `/auth/me` | `GET` | ✓ | ✓ | ✓ | ✗ |
| `/auth/create-staff` | `POST` | ✓ | ✗ | ✗ | ✗ |
| `/auth/refresh` | `POST` | ✓ | ✓ | ✓ | ✗ |
| `/health` | `GET` | ✓ | ✓ | ✓ | ✓ |

### 2.2 Password Validation Rules
Passwords must meet all four requirements:
1. Length: **More than 8 characters** (minimum 9 characters).
2. Uppercase: At least one `[A-Z]`.
3. Lowercase: At least one `[a-z]`.
4. Special Character: At least one from `[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]`.

---

## 3. Endpoints Specification

### 3.1 Authentication

#### `POST /api/v1/auth/register`
Creates a customer account. Automatically bootstraps the very first system user as `admin`.
- **Request Body:**
```json
{
  "email": "customer@company.com",
  "password": "StrongPassword#2026",
  "first_name": "Jane",
  "last_name": "Doe",
  "company_name": "Acme Corp" // Optional
}
```
- **Response (201 Created):**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "user": {
      "id": 1,
      "email": "customer@company.com",
      "first_name": "Jane",
      "last_name": "Doe",
      "role": "customer",
      "is_active": true
    },
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer"
  }
}
```

#### `POST /api/v1/auth/login`
Authenticates credentials and returns JWT tokens.
- **Request Body:**
```json
{
  "email": "admin@subflow.io",
  "password": "SubFlow#Admin2026!"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { "id": 1, "email": "admin@subflow.io", "role": "admin" },
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "Bearer"
  }
}
```

#### `GET /api/v1/auth/me`
Retrieves authenticated user profile and associated customer profile if present.
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Current user profile",
  "data": {
    "id": 1,
    "email": "admin@subflow.io",
    "first_name": "Admin",
    "last_name": "User",
    "role": "admin",
    "is_active": true
  }
}
```

#### `POST /api/v1/auth/create-staff`
**Admin-only endpoint** to provision internal staff accounts.
- **Headers:** `Authorization: Bearer <admin_token>`
- **Request Body:**
```json
{
  "email": "staff1@subflow.io",
  "password": "StaffPassword#2026!",
  "first_name": "Alex",
  "last_name": "Smith"
}
```
- **Response (201 Created):**
```json
{
  "success": true,
  "message": "Staff account successfully created",
  "data": {
    "id": 3,
    "email": "staff1@subflow.io",
    "first_name": "Alex",
    "last_name": "Smith",
    "role": "staff",
    "is_active": true
  }
}
```

---

### 3.2 Dashboard & Reports

#### `GET /api/v1/dashboard/summary`
Returns high-level KPI cards and checks whether the workspace has operational business data.
- **Headers:** `Authorization: Bearer <token>`
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Dashboard summary loaded successfully",
  "data": {
    "is_empty": false,
    "metrics": {
      "active_subscriptions": { "count": 12, "total": 14, "label": "Active Subscriptions" },
      "total_revenue": { "amount": 14250.00, "currency": "USD", "label": "Total Revenue" },
      "outstanding_invoices": { "count": 4, "amount": 3400.00, "currency": "USD", "label": "Outstanding Invoices" },
      "overdue_invoices": { "count": 1, "amount": 850.00, "currency": "USD", "label": "Overdue Invoices" }
    },
    "recent_invoices": [ ... ],
    "recent_subscriptions": [ ... ]
  }
}
```

---

## 4. Feature Developer Integration Guide

The backend includes starter route files in `backend/routes/`. Each teammate is responsible for extending their designated blueprint:

### Blueprint Assignments:
1. **Catalog & Plans Developer:**
   - Extend `backend/routes/products.py` (`POST /products`, `PUT /products/<id>`, variants CRUD).
   - Extend `backend/routes/plans.py` (`POST /plans`, `PUT /plans/<id>`).
2. **Subscriptions & Quotations Developer:**
   - Extend `backend/routes/subscriptions.py` (`POST /subscriptions`, status transitions, pause/renew/cancel).
   - Extend `backend/routes/quotations.py` (`POST /quotations`, send quotation, approve into subscription).
3. **Billing & Payments Developer:**
   - Extend `backend/routes/invoices.py` (`POST /invoices`, line calculations, status updates).
   - Extend `backend/routes/payments.py` (`POST /payments`, allocations against invoice balances).
   - Extend `backend/routes/discounts.py` (`POST /discounts`, redemption logic).

### Shared Coding Utilities:
To maintain consistency, always use the shared helpers:
```python
# 1. Uniform responses
from backend.utils.response import api_response, api_error

# 2. RBAC Decorators
from backend.utils.decorators import role_required, admin_required, staff_or_admin_required, ROLE_ADMIN, ROLE_STAFF

# 3. Query Pagination
from backend.utils.pagination import paginate_query, get_pagination_params

# Example usage in route handler:
@my_bp.route("", methods=["GET"])
@role_required(ROLE_ADMIN, ROLE_STAFF)
def list_items():
    page, per_page = get_pagination_params()
    query = MyModel.query.order_by(MyModel.created_at.desc())
    return api_response(data=paginate_query(query, page, per_page))
```
