import pytest
from datetime import date
from decimal import Decimal
from backend.models import Customer, Invoice, Payment, PaymentAllocation
from backend.services.billing_service import BillingService
from backend.services.payment_service import PaymentService
from backend.extensions import db


@pytest.fixture
def posted_invoice(customer_user):
    inv = BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=date.today(),
        due_date=date.today(),
        lines=[{"description": "Service Subscription", "quantity": 1, "unit_price": 100.00}],
        status="posted"
    )
    db.session.commit()
    return inv


def test_record_payment_with_auto_allocation(customer_user, posted_invoice):
    """Test recording a completed payment that allocates immediately to a target invoice."""
    payment = PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("100.00"),
        payment_method="credit_card",
        status="completed",
        invoice_id=posted_invoice.id,
        transaction_reference="ch_test_12345"
    )
    db.session.commit()

    assert payment.payment_number.startswith("PAY-")
    assert payment.amount == Decimal("100.00")

    # Verify invoice was reconciled to Paid
    inv = db.session.get(Invoice, posted_invoice.id)
    assert inv.status == "paid"
    assert inv.amount_paid == Decimal("100.00")
    assert inv.balance_due == Decimal("0.00")

    # Verify allocation record
    alloc = PaymentAllocation.query.filter_by(payment_id=payment.id, invoice_id=inv.id).first()
    assert alloc is not None
    assert alloc.amount_allocated == Decimal("100.00")


def test_partial_payment_reconciliation(customer_user, posted_invoice):
    """Test partial payment reconciliation sets status to 'partial'."""
    payment = PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("40.00"),
        status="completed",
        invoice_id=posted_invoice.id
    )
    db.session.commit()

    inv = db.session.get(Invoice, posted_invoice.id)
    assert inv.status == "partial"
    assert inv.amount_paid == Decimal("40.00")
    assert inv.balance_due == Decimal("60.00")


def test_multi_invoice_allocation(customer_user):
    """Test allocating one payment across multiple invoices."""
    inv1 = BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=date.today(),
        due_date=date.today(),
        lines=[{"description": "Inv 1", "quantity": 1, "unit_price": 60.00}],
        status="posted"
    )
    inv2 = BillingService.create_invoice(
        customer_id=customer_user.customer_id,
        invoice_date=date.today(),
        due_date=date.today(),
        lines=[{"description": "Inv 2", "quantity": 1, "unit_price": 40.00}],
        status="posted"
    )
    db.session.commit()

    # Record unallocated lump-sum payment of $100
    payment = PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("100.00"),
        status="completed"
    )
    db.session.commit()

    # Allocate across inv1 and inv2
    alloc_res = PaymentService.allocate_payment(
        payment_id=payment.id,
        allocations=[
            {"invoice_id": inv1.id, "amount": 60.00},
            {"invoice_id": inv2.id, "amount": 40.00}
        ]
    )

    assert alloc_res["total_allocated_now"] == 100.00
    assert alloc_res["remaining_unallocated"] == 0.00

    inv1_reloaded = db.session.get(Invoice, inv1.id)
    inv2_reloaded = db.session.get(Invoice, inv2.id)
    assert inv1_reloaded.status == "paid"
    assert inv2_reloaded.status == "paid"


def test_forbidden_cross_customer_allocation(customer_user, posted_invoice):
    """Test that allocating payment to another customer's invoice is forbidden."""
    from backend.models import User
    other_user = User(email="third.user@subflow.io", first_name="3rd", last_name="User", role="customer")
    other_user.set_password("SubFlow#Customer2026!")
    db.session.add(other_user)
    db.session.flush()

    other_customer = Customer(
        user_id=other_user.id,
        company_name="Different Co",
        contact_name="Bob",
        email=other_user.email
    )
    db.session.add(other_customer)
    db.session.commit()

    # Payment belongs to other_customer
    pay = PaymentService.record_payment(
        customer_id=other_customer.id,
        amount=Decimal("50.00"),
        status="completed"
    )
    db.session.commit()

    # Attempt to allocate to posted_invoice (which belongs to customer_user)
    with pytest.raises(ValueError, match="Cross-customer allocation is forbidden"):
        PaymentService.allocate_payment(
            payment_id=pay.id,
            allocations=[{"invoice_id": posted_invoice.id, "amount": 50.00}]
        )


def test_allocation_exceeding_balance_rejected(customer_user, posted_invoice):
    """Test that allocating more than invoice balance_due is rejected."""
    pay = PaymentService.record_payment(
        customer_id=customer_user.customer_id,
        amount=Decimal("200.00"),
        status="completed"
    )
    db.session.commit()

    # Invoice balance is 100.00, attempting to allocate 150.00
    with pytest.raises(ValueError, match="exceeds invoice"):
        PaymentService.allocate_payment(
            payment_id=pay.id,
            allocations=[{"invoice_id": posted_invoice.id, "amount": 150.00}]
        )
