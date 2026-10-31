# SubFlow — Subscription Management System

> **Make-A-Ton 9.0 Hackathon Foundation**  
> Core Platform & Integration Foundation: Architecture, Authentication, Role-Based Access Control (RBAC), Shared Neon PostgreSQL Foundation, API Conventions, and Responsive SaaS Dashboard.

---

## 1. Project Overview

**SubFlow** is an enterprise-grade Subscription Management System designed to handle complex recurring lifecycles, quotation-to-subscription conversions, flexible billing cadences, discount rules, receivables, and payment allocations.

This repository serves as the **shared core foundation** for a team of 4 developers. It establishes:
- Secure JWT-based Authentication & Password Complexity Enforcement.
- Role-Based Access Control (RBAC) with three distinct tiers: **Admin**, **Staff**, and **Customer**.
- PostgreSQL-compatible SQLAlchemy ORM models with `Numeric(12, 2)` decimal arithmetic for monetary precision.
- Neon PostgreSQL connectivity with automatic connection string normalization and connection pool recycling.
- Flask-Migrate / Alembic migration version control.
- Uniform API envelope standards and error handling under `/api/v1`.
- Modern, responsive React.js + Vite dashboard featuring Tailwind CSS, Lucide icons, and Recharts.
- Clear empty states across incomplete business modules.
- Comprehensive automated test suite for authentication, RBAC, validators, and health check.

---

## 2. Technology Stack

- **Frontend:** React 19, Vite, Tailwind CSS, Lucide Icons, Recharts, Axios
- **Backend:** Python 3.13, Flask 3.1, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS
- **Database:** PostgreSQL on Neon (with automatic fallback to local SQLite for rapid dev)
- **Authentication:** Salted PBKDF2/SHA256 password hashing, JWT Bearer tokens
- **Testing:** Pytest, Pytest-Flask

---

## 3. Directory Structure

```text
SubFlow/
├── backend/
│   ├── app.py                   # Application factory & CLI seed commands
│   ├── config.py                # Environment configurations (Dev, Test, Prod)
│   ├── extensions.py            # Initialized db, migrate, jwt, cors
│   ├── models/                  # Shared SQLAlchemy database models
│   │   ├── __init__.py          # Exports all models for Alembic discovery
│   │   ├── user.py              # User entity with password hashing & RBAC
│   │   ├── customer.py          # Customer company & billing profiles
│   │   ├── product.py           # Products & ProductVariants
│   │   ├── plan.py              # Subscription Plans & billing intervals
│   │   ├── quotation.py         # Quotations & QuotationLines
│   │   ├── subscription.py      # Subscriptions & SubscriptionLines
│   │   ├── invoice.py           # Invoices & InvoiceLines
│   │   ├── discount.py          # DiscountRules engine
│   │   ├── payment.py           # Payments & PaymentAllocations
│   │   └── audit_log.py         # AuditLog compliance records
│   ├── routes/                  # API v1 blueprint route handlers
│   │   ├── __init__.py          # Blueprint registrar
│   │   ├── auth.py              # Login, register, create-staff, me
│   │   ├── dashboard.py         # Summary metrics & empty state signals
│   │   ├── health.py            # System & DB connectivity health check
│   │   ├── products.py          # Products module starter
│   │   ├── plans.py             # Plans module starter
│   │   ├── subscriptions.py     # Subscriptions module starter
│   │   ├── quotations.py        # Quotations module starter
│   │   ├── invoices.py          # Invoices module starter
│   │   ├── payments.py          # Payments module starter
│   │   ├── discounts.py         # Discounts module starter
│   │   └── reports.py           # Recharts analytical endpoints
│   ├── utils/                   # Shared API helpers, RBAC decorators, validators
│   ├── migrations/              # Flask-Migrate / Alembic version scripts
│   ├── tests/                   # Pytest test suite (17 passing tests)
│   ├── requirements.txt         # Backend Python dependencies
│   └── .env.example             # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # Sidebar, Navbar, AppLayout
│   │   │   ├── common/          # StatCard, EmptyState, LoadingSpinner, Alert, CreateStaffModal
│   │   │   └── ui/              # Button, Input, Card, Badge, Modal, Table
│   │   ├── pages/               # Dashboard, Login, Register, Products, Plans, Subscriptions, etc.
│   │   ├── services/            # Axios API client & services layer
│   │   ├── hooks/               # useAuth hook & AuthContext
│   │   ├── lib/                 # Tailwind utility helpers & formatters
│   │   ├── App.jsx              # Main router & layout coordinator
│   │   ├── main.jsx             # React DOM root
│   │   └── index.css            # Custom CSS & Tailwind base
│   ├── package.json             # Frontend NPM dependencies
│   ├── tailwind.config.js       # Tailwind configuration
│   └── .env.example             # Frontend environment template
├── docs/
│   ├── database-schema.md       # Complete DB schema, ERD, and table definitions
│   └── api-contracts.md         # API contracts, response envelopes & team guide
├── .gitignore                   # Multi-tier gitignore (secrets, venv, node_modules)
├── .env.example                 # Root environment reference
├── pytest.ini                   # Pytest root configuration
└── README.md                    # Project documentation
```

---

## 4. Quick Start Guide

### 4.1 Backend Setup

1. **Activate Python Virtual Environment:**
   ```bash
   # Windows PowerShell
   .\backend\venv\Scripts\Activate.ps1

   # Linux / macOS
   source backend/venv/bin/activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment:**
   Copy `backend/.env.example` to `backend/.env`.
   ```bash
   cp backend/.env.example backend/.env
   ```
   *(Note: If `DATABASE_URL` is omitted, the app will automatically initialize a local SQLite database `subflow_dev.db` for instant offline testing).*

4. **Run Database Migrations & Seed Demo Accounts:**
   ```bash
   # Set Flask App variable
   $env:FLASK_APP="backend.app"   # Windows
   export FLASK_APP=backend.app   # Linux/macOS

   # Apply migrations
   flask db upgrade -d backend/migrations

   # Seed default demo accounts and plans
   flask seed
   ```

5. **Start Flask Server:**
   ```bash
   python backend/app.py
   # Server runs on http://localhost:5000 (API prefix: http://localhost:5000/api/v1)
   ```

6. **Run Backend Tests:**
   ```bash
   pytest -v
   ```

---

### 4.2 Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install NPM packages:**
   ```bash
   npm install
   ```

3. **Start the Vite development server:**
   ```bash
   npm run dev
   # Frontend runs on http://localhost:5173
   ```

4. **Build Production Bundle:**
   ```bash
   npm run build
   ```

---

## 5. Pre-seeded Demo Accounts

For rapid hackathon testing and judging, running `flask seed` automatically provisions these test accounts:

| Role | Email | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@subflow.io` | `SubFlow#Admin2026!` | Full administrative access, staff provisioning, all modules |
| **Staff** | `staff@subflow.io` | `SubFlow#Staff2026!` | Quotations, subscriptions, invoicing, catalog, reports |
| **Customer** | `customer@subflow.io` | `SubFlow#Customer2026!` | Customer self-service, view invoices, view subscriptions |

*Tip: The login screen contains one-click demo account selector pills for instant evaluation.*

---

## 6. Password Security Validation

All account registrations and staff creations enforce the following strict criteria:
- **Length:** More than 8 characters (minimum 9 characters).
- **Uppercase:** At least one uppercase letter `[A-Z]`.
- **Lowercase:** At least one lowercase letter `[a-z]`.
- **Special Character:** At least one symbol from `[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]`.

---

## 7. Connecting to Neon PostgreSQL

To connect SubFlow to your Neon serverless PostgreSQL instance:

1. Create a project on [Neon.tech](https://neon.tech).
2. Copy your connection URI from the Neon console.
3. Update `DATABASE_URL` in `backend/.env`:
   ```env
   DATABASE_URL=postgresql://user:password@ep-your-branch.us-east-2.aws.neon.tech/subflow?sslmode=require
   ```
4. Run migrations:
   ```bash
   flask db upgrade -d backend/migrations
   flask seed
   ```

---

## 8. Team Collaboration Guidelines

To avoid merge conflicts among the 4 developers:

1. **Shared Foundation:** Do not modify `backend/extensions.py` or database column types in existing models without coordinating with the team.
2. **Modular Blueprints:** Each feature developer works within their assigned route file in `backend/routes/`:
   - **Teammate A (Catalog & Plans):** `backend/routes/products.py` & `backend/routes/plans.py`
   - **Teammate B (Subscriptions & Quotations):** `backend/routes/subscriptions.py` & `backend/routes/quotations.py`
   - **Teammate C (Invoicing & Payments):** `backend/routes/invoices.py`, `backend/routes/payments.py`, & `backend/routes/discounts.py`
3. **Use Shared Helpers:** Always utilize `api_response`, `api_error`, and `paginate_query` from `backend.utils`.
4. **API Contracts:** Refer to `docs/api-contracts.md` for exact request/response envelopes.
5. **Database Schema:** Refer to `docs/database-schema.md` for entity relationships and foreign keys.
