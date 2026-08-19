"""Add fields required by real legacy workbook formats.

Revision ID: 20260819_0002
Revises: 20260813_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260819_0002"
down_revision = "20260813_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    review_columns = (
        sa.Column("review_type", sa.String(40)),
        sa.Column("manuscript_title", sa.String(500)),
        sa.Column("department", sa.String(160)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(40)),
        sa.Column("bank_name", sa.String(255)),
        sa.Column("bank_account_name", sa.String(160)),
        sa.Column("bank_account", sa.String(80)),
        sa.Column("clearing_no", sa.String(40)),
        sa.Column("source_sheet", sa.String(160)),
        sa.Column("source_row", sa.Integer()),
    )
    page_columns = (
        sa.Column("paid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voucher_no", sa.String(80)),
        sa.Column("phone", sa.String(40)),
        sa.Column("source_sheet", sa.String(160)),
        sa.Column("source_row", sa.Integer()),
    )
    royalty_columns = (
        sa.Column("phone", sa.String(40)),
        sa.Column("id_card", sa.String(40)),
        sa.Column("bank_name", sa.String(255)),
        sa.Column("bank_account_name", sa.String(160)),
        sa.Column("bank_account", sa.String(80)),
        sa.Column("clearing_no", sa.String(40)),
        sa.Column("source_sheet", sa.String(160)),
        sa.Column("source_row", sa.Integer()),
    )
    batch_columns = (sa.Column("source_sheet", sa.String(160)),)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    for table_name, columns in (
        ("review_fees", review_columns),
        ("page_fees", page_columns),
        ("royalties", royalty_columns),
        ("processing_batches", batch_columns),
    ):
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table_name, column)


def downgrade() -> None:
    op.drop_column("processing_batches", "source_sheet")
    for name in (
        "source_row",
        "source_sheet",
        "clearing_no",
        "bank_account",
        "bank_account_name",
        "bank_name",
        "phone",
        "email",
        "department",
        "manuscript_title",
        "review_type",
    ):
        op.drop_column("review_fees", name)
    for name in ("source_row", "source_sheet", "phone", "voucher_no", "paid"):
        op.drop_column("page_fees", name)
    for name in (
        "source_row",
        "source_sheet",
        "clearing_no",
        "bank_account",
        "bank_account_name",
        "bank_name",
        "id_card",
        "phone",
    ):
        op.drop_column("royalties", name)
