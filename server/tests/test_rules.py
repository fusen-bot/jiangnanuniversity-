from decimal import Decimal

from app.models import PageFee, ReviewFee, Royalty
from app.services.rules import (
    calculate_review_fee,
    calculate_royalty,
    is_internal,
    validate_page_fee,
    validate_review_fee,
    validate_royalty,
)


def test_review_fee_rules_cover_internal_and_external_reviewers():
    internal = ReviewFee(batch_id="b", manuscript_no="M1", reviewer_name="张三", is_internal=True)
    external = ReviewFee(
        batch_id="b",
        manuscript_no="M2",
        reviewer_name="李四",
        is_internal=False,
        amount=Decimal("150.00"),
    )
    assert is_internal("江南大学食品学院")
    assert calculate_review_fee(internal) == Decimal("100.00")
    assert calculate_review_fee(external) == Decimal("150.00")
    assert {issue[0] for issue in validate_review_fee(internal)} == {"missing_employee_no"}
    assert {issue[0] for issue in validate_review_fee(external)} == {"missing_id_card", "missing_bank_account"}


def test_page_fee_and_royalty_validation():
    page_fee = PageFee(batch_id="b", manuscript_no="M1", accepted=True, invoiced=True)
    assert {issue[0] for issue in validate_page_fee(page_fee)} == {
        "missing_tax_no",
        "missing_invoice_title",
        "missing_email",
    }
    royalty = Royalty(batch_id="b", manuscript_no="M1", author_name="王五", is_internal=True, eligible=False)
    assert calculate_royalty(royalty) == Decimal("0.00")
    assert {issue[0] for issue in validate_royalty(royalty)} == {"missing_employee_no"}
