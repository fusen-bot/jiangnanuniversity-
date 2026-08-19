from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

from app.enums import BusinessType

COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "manuscript_no": ("稿件编号", "稿件号", "*开票依据编号", "manuscript_no", "稿号"),
    "manuscript_title": ("稿件标题", "标题", "文章标题", "题名", "article_title"),
    "review_type": ("审稿类型", "review_type"),
    "reviewer_name": ("审稿人姓名", "审稿人", "reviewer_name", "姓名"),
    "author_name": ("作者", "通信作者", "第一作者", "一作姓名", "author_name"),
    "employee_no": ("工号", "employee_no"),
    "id_card": ("身份证号", "审稿人身份证号", "证件号码(必填)", "id_card"),
    "institution": ("审稿人单位", "工作单位", "单位", "institution", "作者单位"),
    "department": ("部门", "department"),
    "status": ("状态", "稿件状态", "status"),
    "accepted": ("录用", "accepted"),
    "invoiced": ("发票", "发票开具", "author_invoice_registered", "invoiced"),
    "paid": ("收款", "财务是否到账", "paid"),
    "reimbursement_no": ("核销号", "财务核销代码", "往来核销号", "reimbursement_no"),
    "voucher_no": ("凭证号", "voucher_no"),
    "tax_no": ("税号", "统一社会信用代码", "境外纳税人识别号", "tax_no"),
    "invoice_title": ("抬头", "发票抬头", "*开票单位名称", "invoice_title"),
    "email": ("邮箱", "审稿人E-mail", "*推送邮箱", "通信邮箱", "发送邮箱", "email"),
    "phone": ("电话", "审稿人手机", "审稿人电话", "手机号码(必填)", "*推送手机", "phone"),
    "amount": ("金额", "审稿费金额", "*开票金额", "amount"),
    "eligible": ("是否发稿费", "eligible"),
    "bank_name": ("开户银行", "开户行", "开户行名(必填)", "bank_name"),
    "bank_account_name": ("银行账户名", "银行账户名称", "银行户名", "bank_account_name"),
    "bank_account": ("银行卡号", "银行账号", "银行账号(必填)", "账号", "bank_account"),
    "clearing_no": ("联行号", "联行号(必填)", "银联号", "clearing_no"),
    "review_returned_at": ("审回时间", "review_returned_at"),
    "received_at": ("审理费缴纳时间", "到款日期", "received_at"),
}

PROFILE_FIELDS: Final[dict[BusinessType, tuple[str, ...]]] = {
    BusinessType.REVIEW_FEE: (
        "manuscript_no",
        "reviewer_name",
        "review_type",
        "institution",
        "amount",
        "employee_no",
        "id_card",
        "bank_account",
    ),
    BusinessType.PAGE_FEE: (
        "manuscript_no",
        "status",
        "paid",
        "reimbursement_no",
        "invoice_title",
        "tax_no",
        "email",
    ),
    BusinessType.ROYALTY: (
        "manuscript_no",
        "author_name",
        "manuscript_title",
        "amount",
        "id_card",
        "bank_account",
    ),
}

SENSITIVE_FIELDS: Final[set[str]] = {
    "id_card",
    "tax_no",
    "email",
    "phone",
    "bank_account",
    "clearing_no",
}


@dataclass(frozen=True)
class DetectedTable:
    dataframe: pd.DataFrame
    sheet_name: str
    header_row: int
    matched_fields: tuple[str, ...]


def normalized_field(column_name: object) -> str | None:
    text = str(column_name).strip()
    for field, aliases in COLUMN_ALIASES.items():
        if text in aliases:
            return field
    return None


def detect_table(
    sheets: dict[str, pd.DataFrame],
    business_type: BusinessType,
    preferred_sheet: str | None = None,
) -> DetectedTable:
    if preferred_sheet and preferred_sheet not in sheets:
        raise ValueError(f"工作表不存在：{preferred_sheet}")
    candidates = {preferred_sheet: sheets[preferred_sheet]} if preferred_sheet else sheets
    best: tuple[int, str, int, list[object], tuple[str, ...]] | None = None
    expected = set(PROFILE_FIELDS[business_type])
    for sheet_name, raw in candidates.items():
        for row_index in range(min(len(raw), 30)):
            values = list(raw.iloc[row_index])
            matched = tuple(dict.fromkeys(field for value in values if (field := normalized_field(value)) in expected))
            candidate = (len(matched), sheet_name, row_index, values, matched)
            if best is None or candidate[0] > best[0]:
                best = candidate
    if best is None or best[0] < 2:
        raise ValueError(f"无法识别 {business_type.value} 工作表表头")
    _, sheet_name, row_index, headers, matched = best
    dataframe = sheets[sheet_name].iloc[row_index + 1 :].copy()
    dataframe.columns = [
        str(value).strip() if value is not None and str(value) != "nan" else f"unnamed_{index}"
        for index, value in enumerate(headers)
    ]
    dataframe = dataframe.dropna(how="all").reset_index(drop=True)
    return DetectedTable(
        dataframe=dataframe,
        sheet_name=sheet_name,
        header_row=row_index + 1,
        matched_fields=matched,
    )
