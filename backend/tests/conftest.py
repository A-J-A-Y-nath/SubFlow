import pytest
from types import SimpleNamespace
from backend.app import create_app
from backend.extensions import db
from backend.models import User, Customer


@pytest.fixture(scope="session")
def app():
    """Create application configured for testing with in-memory database."""
    app = create_app("testing")
    return app


@pytest.fixture(autouse=True)
def app_context(app):
    """Provide application context and recreate database for every test."""
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Create a persistent test Admin user."""
    with app.app_context():
        user = User(
            email="admin.test@subflow.io",
            first_name="Admin",
            last_name="Tester",
            role="admin",
            is_active=True
        )
        user.set_password("SubFlow#Admin2026!")
        db.session.add(user)
        db.session.commit()
        return SimpleNamespace(
            id=user.id,
            email="admin.test@subflow.io",
            password="SubFlow#Admin2026!",
            role="admin"
        )


@pytest.fixture
def customer_user(app):
    """Create a persistent test Customer user."""
    with app.app_context():
        user = User(
            email="customer.test@subflow.io",
            first_name="Customer",
            last_name="Tester",
            role="customer",
            is_active=True
        )
        user.set_password("SubFlow#Customer2026!")
        db.session.add(user)
        db.session.flush()

        customer = Customer(
            user_id=user.id,
            company_name="Acme Testing Corp",
            contact_name="Customer Tester",
            email=user.email,
        )
        db.session.add(customer)
        db.session.commit()
        return SimpleNamespace(
            id=user.id,
            email="customer.test@subflow.io",
            password="SubFlow#Customer2026!",
            role="customer",
            customer_id=customer.id
        )


@pytest.fixture
def admin_token(client, admin_user):
    """Helper that logs in as admin and returns the Bearer access token."""
    res = client.post("/api/v1/auth/login", json={
        "email": admin_user.email,
        "password": admin_user.password
    })
    return res.json["data"]["access_token"]


@pytest.fixture
def customer_token(client, customer_user):
    """Helper that logs in as customer and returns the Bearer access token."""
    res = client.post("/api/v1/auth/login", json={
        "email": customer_user.email,
        "password": customer_user.password
    })
    return res.json["data"]["access_token"]
