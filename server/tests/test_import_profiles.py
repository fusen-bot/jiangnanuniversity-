import pandas as pd

from app.enums import BusinessType
from app.services.import_export import _status_flags, _value
from app.services.import_profiles import SENSITIVE_FIELDS, detect_table, normalized_field


def test_detects_real_review_fee_header_in_multi_sheet_workbook():
    sheets = {
        "说明": pd.DataFrame([["导入说明"], ["请勿修改"]]),
        "审稿费": pd.DataFrame(
            [
                ["2026年3月审稿费统计"],
                ["审稿类型", "稿件编号", "审稿人姓名", "审稿人单位", "审稿费金额", "银行账号"],
                ["评审", "DEMO-001", "模拟人员甲", "示例大学", 150, "6222000000000000000"],
            ]
        ),
    }
    detected = detect_table(sheets, BusinessType.REVIEW_FEE)
    assert detected.sheet_name == "审稿费"
    assert detected.header_row == 2
    assert detected.matched_fields == (
        "review_type",
        "manuscript_no",
        "reviewer_name",
        "institution",
        "amount",
        "bank_account",
    )
    row = detected.dataframe.iloc[0]
    assert _value(row, "reviewer_name") == "模拟人员甲"
    assert _value(row, "amount") == 150


def test_maps_real_page_fee_and_royalty_aliases():
    page_row = pd.Series(
        {
            "稿件编号": "DEMO-002",
            "状态": "录用, 发票",
            "收款": "是",
            "抬头": "模拟机构",
            "凭证号": "PZ-DEMO-001",
        }
    )
    assert _status_flags(page_row) == (True, True)
    assert _value(page_row, "invoice_title") == "模拟机构"
    assert _value(page_row, "voucher_no") == "PZ-DEMO-001"
    assert normalized_field("审稿人E-mail") == "email"
    assert normalized_field("银行卡号") == "bank_account"
    assert {"id_card", "tax_no", "bank_account", "email"} <= SENSITIVE_FIELDS


def test_explicit_sheet_selection_avoids_importing_derived_subset():
    sheets = {
        "Sheet1": pd.DataFrame([["稿件编号", "审稿人姓名"], ["DEMO-001", "模拟人员甲"]]),
        "校内": pd.DataFrame([["稿件编号", "审稿人姓名", "工号"], ["DEMO-002", "模拟人员乙", "E001"]]),
    }
    detected = detect_table(sheets, BusinessType.REVIEW_FEE, preferred_sheet="Sheet1")
    assert detected.sheet_name == "Sheet1"
    assert detected.dataframe.iloc[0]["稿件编号"] == "DEMO-001"
