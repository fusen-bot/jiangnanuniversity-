from decimal import Decimal

from app.models import PageFee, ReviewFee, Royalty

INTERNAL_KEYWORDS = ("江南大学", "蠡湖大道", "1800号")


def is_internal(institution: str | None) -> bool:
    text = institution or ""
    return any(keyword in text for keyword in INTERNAL_KEYWORDS)


def calculate_review_fee(record: ReviewFee) -> Decimal:
    return Decimal("100.00") if record.is_internal else Decimal("150.00")


def calculate_royalty(record: Royalty) -> Decimal:
    if not record.eligible:
        return Decimal("0.00")
    return Decimal("150.00")


def validate_review_fee(record: ReviewFee) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    if not record.manuscript_no.strip():
        issues.append(("missing_manuscript", "error", "稿件编号不能为空"))
    if not record.reviewer_name.strip():
        issues.append(("missing_reviewer", "error", "审稿人不能为空"))
    if record.is_internal and not record.employee_no:
        issues.append(("missing_employee_no", "warning", "校内审稿人缺少工号"))
    if not record.is_internal and not record.id_card:
        issues.append(("missing_id_card", "warning", "校外审稿人缺少身份证号"))
    if not record.is_internal and record.amount > 0 and not record.bank_account:
        issues.append(("missing_bank_account", "warning", "校外审稿人缺少银行账号"))
    return issues


def validate_page_fee(record: PageFee) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    if record.invoiced and not record.tax_no:
        issues.append(("missing_tax_no", "warning", "已开票记录缺少税号"))
    if record.invoiced and not record.invoice_title:
        issues.append(("missing_invoice_title", "warning", "已开票记录缺少发票抬头"))
    if record.accepted and not record.email:
        issues.append(("missing_email", "warning", "已录用稿件缺少联系邮箱"))
    return issues


def validate_royalty(record: Royalty) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    if not record.author_name.strip():
        issues.append(("missing_author", "error", "作者姓名不能为空"))
    if record.is_internal and not record.employee_no:
        issues.append(("missing_employee_no", "warning", "校内作者缺少工号"))
    if record.eligible and not record.email:
        issues.append(("missing_email", "warning", "符合稿费条件的作者缺少邮箱"))
    if record.eligible and record.amount > 0 and not record.bank_account:
        issues.append(("missing_bank_account", "warning", "符合稿费条件的作者缺少银行账号"))
    return issues
