from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import BusinessType
from app.models import PageFee, ProcessingBatch, ReviewFee, Royalty, StoredFile, User, new_id
from app.services.import_profiles import COLUMN_ALIASES, DetectedTable, detect_table
from app.storage import resolve_stored_file


def _value(row: pd.Series, key: str, default: Any = None) -> Any:
    for alias in COLUMN_ALIASES[key]:
        if alias in row and pd.notna(row[alias]):
            return row[alias]
    return default


def _text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "是", "已完成", "录用", "发票"}


def _amount(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def read_tabular_file(
    path: Path,
    business_type: BusinessType,
    preferred_sheet: str | None = None,
) -> DetectedTable:
    if path.suffix.lower() == ".csv":
        dataframe = pd.read_csv(path)
        return DetectedTable(dataframe=dataframe, sheet_name="CSV", header_row=1, matched_fields=())
    sheets = pd.read_excel(path, sheet_name=None, header=None)
    return detect_table(sheets, business_type, preferred_sheet)


def _status_flags(row: pd.Series) -> tuple[bool, bool]:
    status_text = (_text(_value(row, "status")) or "").lower()
    accepted = _bool(_value(row, "accepted")) or "录用" in status_text or "已完成" in status_text
    invoiced = _bool(_value(row, "invoiced")) or "发票" in status_text or "已完成" in status_text
    return accepted, invoiced


def import_batch_file(db: Session, batch: ProcessingBatch) -> int:
    if not batch.source_file:
        return 0
    detected = read_tabular_file(resolve_stored_file(batch.source_file), batch.business_type, batch.source_sheet)
    dataframe = detected.dataframe.fillna("")
    count = 0
    for row_offset, (_, row) in enumerate(dataframe.iterrows()):
        manuscript_no = _text(_value(row, "manuscript_no")) or ""
        source_row = detected.header_row + row_offset + 1
        if batch.business_type == BusinessType.REVIEW_FEE:
            db.add(
                ReviewFee(
                    batch_id=batch.id,
                    manuscript_no=manuscript_no,
                    reviewer_name=_text(_value(row, "reviewer_name")) or "",
                    review_type=_text(_value(row, "review_type")),
                    manuscript_title=_text(_value(row, "manuscript_title")),
                    employee_no=_text(_value(row, "employee_no")),
                    id_card=_text(_value(row, "id_card")),
                    institution=_text(_value(row, "institution")),
                    department=_text(_value(row, "department")),
                    email=_text(_value(row, "email")),
                    phone=_text(_value(row, "phone")),
                    bank_name=_text(_value(row, "bank_name")),
                    bank_account_name=_text(_value(row, "bank_account_name")),
                    bank_account=_text(_value(row, "bank_account")),
                    clearing_no=_text(_value(row, "clearing_no")),
                    amount=_amount(_value(row, "amount")),
                    source_sheet=detected.sheet_name,
                    source_row=source_row,
                )
            )
        elif batch.business_type == BusinessType.PAGE_FEE:
            accepted, invoiced = _status_flags(row)
            db.add(
                PageFee(
                    batch_id=batch.id,
                    manuscript_no=manuscript_no,
                    accepted=accepted,
                    invoiced=invoiced,
                    paid=_bool(_value(row, "paid")),
                    reimbursement_no=_text(_value(row, "reimbursement_no")),
                    voucher_no=_text(_value(row, "voucher_no")),
                    tax_no=_text(_value(row, "tax_no")),
                    invoice_title=_text(_value(row, "invoice_title")),
                    email=_text(_value(row, "email")),
                    phone=_text(_value(row, "phone")),
                    amount=_amount(_value(row, "amount")),
                    source_sheet=detected.sheet_name,
                    source_row=source_row,
                )
            )
        else:
            db.add(
                Royalty(
                    batch_id=batch.id,
                    manuscript_no=manuscript_no,
                    article_title=_text(_value(row, "manuscript_title")),
                    author_name=_text(_value(row, "author_name")) or "",
                    institution=_text(_value(row, "institution")),
                    email=_text(_value(row, "email")),
                    phone=_text(_value(row, "phone")),
                    id_card=_text(_value(row, "id_card")),
                    bank_name=_text(_value(row, "bank_name")),
                    bank_account_name=_text(_value(row, "bank_account_name")),
                    bank_account=_text(_value(row, "bank_account")),
                    clearing_no=_text(_value(row, "clearing_no")),
                    employee_no=_text(_value(row, "employee_no")),
                    eligible=_bool(_value(row, "eligible", True)),
                    amount=_amount(_value(row, "amount")),
                    source_sheet=detected.sheet_name,
                    source_row=source_row,
                )
            )
        count += 1
    batch.row_count = count
    return count


def export_batch(db: Session, batch: ProcessingBatch, user: User, output_dir: Path) -> StoredFile:
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    assert isinstance(sheet, Worksheet)
    sheet.title = "财务数据"

    if batch.business_type == BusinessType.REVIEW_FEE:
        review_rows = list(db.scalars(select(ReviewFee).where(ReviewFee.batch_id == batch.id)))
        headers = [
            "审稿类型",
            "稿件编号",
            "稿件标题",
            "审稿人",
            "工号",
            "身份证号",
            "单位",
            "邮箱",
            "电话",
            "开户银行",
            "银行账户名",
            "银行账号",
            "联行号",
            "是否校内",
            "金额",
            "来源工作表",
            "来源行",
        ]
        values = [
            [
                r.review_type,
                r.manuscript_no,
                r.manuscript_title,
                r.reviewer_name,
                r.employee_no,
                r.id_card,
                r.institution,
                r.email,
                r.phone,
                r.bank_name,
                r.bank_account_name,
                r.bank_account,
                r.clearing_no,
                r.is_internal,
                r.amount,
                r.source_sheet,
                r.source_row,
            ]
            for r in review_rows
        ]
    elif batch.business_type == BusinessType.PAGE_FEE:
        page_rows = list(db.scalars(select(PageFee).where(PageFee.batch_id == batch.id)))
        headers = [
            "稿件编号",
            "录用",
            "发票",
            "到账",
            "核销号",
            "凭证号",
            "税号",
            "发票抬头",
            "邮箱",
            "电话",
            "金额",
            "来源工作表",
            "来源行",
        ]
        values = [
            [
                r.manuscript_no,
                r.accepted,
                r.invoiced,
                r.paid,
                r.reimbursement_no,
                r.voucher_no,
                r.tax_no,
                r.invoice_title,
                r.email,
                r.phone,
                r.amount,
                r.source_sheet,
                r.source_row,
            ]
            for r in page_rows
        ]
    else:
        royalty_rows = list(db.scalars(select(Royalty).where(Royalty.batch_id == batch.id)))
        headers = [
            "稿件编号",
            "文章标题",
            "作者",
            "单位",
            "邮箱",
            "电话",
            "身份证号",
            "工号",
            "开户银行",
            "银行账户名",
            "银行卡号",
            "联行号",
            "是否校内",
            "是否发稿费",
            "金额",
            "来源工作表",
            "来源行",
        ]
        values = [
            [
                r.manuscript_no,
                r.article_title,
                r.author_name,
                r.institution,
                r.email,
                r.phone,
                r.id_card,
                r.employee_no,
                r.bank_name,
                r.bank_account_name,
                r.bank_account,
                r.clearing_no,
                r.is_internal,
                r.eligible,
                r.amount,
                r.source_sheet,
                r.source_row,
            ]
            for r in royalty_rows
        ]

    sheet.append(headers)
    for row in values:
        sheet.append(row)
    storage_name = f"{new_id()}.xlsx"
    destination = output_dir / storage_name
    workbook.save(destination)
    content = destination.read_bytes()
    import hashlib

    return StoredFile(
        original_name=f"{batch.name}-v{batch.version}.xlsx",
        storage_name=storage_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        category="export",
        uploaded_by_id=user.id,
    )
