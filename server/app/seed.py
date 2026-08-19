from decimal import Decimal

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.enums import BatchStatus, BusinessType, RoleCode
from app.models import KnowledgeDocument, PageFee, ProcessingBatch, Role, User
from app.security import hash_password

ROLE_NAMES = {
    RoleCode.ADMIN: "系统管理员",
    RoleCode.OPERATOR: "财务经办人",
    RoleCode.APPROVER: "审批人",
    RoleCode.VIEWER: "只读人员",
}

DEMO_USERS = (
    ("admin", "管理员", "Admin123!", RoleCode.ADMIN),
    ("operator", "财务经办人", "Operator123!", RoleCode.OPERATOR),
    ("approver", "财务审批人", "Approver123!", RoleCode.APPROVER),
    ("viewer", "只读用户", "Viewer123!", RoleCode.VIEWER),
)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        roles: dict[RoleCode, Role] = {}
        for code, name in ROLE_NAMES.items():
            role = db.scalar(select(Role).where(Role.code == code.value))
            if not role:
                role = Role(code=code.value, name=name)
                db.add(role)
                db.flush()
            roles[code] = role

        users: dict[str, User] = {}
        for username, display_name, password, role_code in DEMO_USERS:
            user = db.scalar(select(User).where(User.username == username))
            if not user:
                user = User(
                    username=username,
                    display_name=display_name,
                    password_hash=hash_password(password),
                    roles=[roles[role_code]],
                )
                db.add(user)
                db.flush()
            users[username] = user

        if not db.scalar(select(ProcessingBatch).limit(1)):
            batch = ProcessingBatch(
                name="2026年第1期版面费演示批次",
                business_type=BusinessType.PAGE_FEE,
                status=BatchStatus.PENDING_REVIEW,
                row_count=2,
                issue_count=0,
                created_by_id=users["operator"].id,
            )
            db.add(batch)
            db.flush()
            db.add_all(
                [
                    PageFee(
                        batch_id=batch.id,
                        manuscript_no="DEMO-2026-001",
                        accepted=True,
                        invoiced=True,
                        reimbursement_no="HX-DEMO-001",
                        tax_no="91320200DEMO00001",
                        invoice_title="示例研究机构",
                        email="author1@example.com",
                        amount=Decimal("2600.00"),
                    ),
                    PageFee(
                        batch_id=batch.id,
                        manuscript_no="DEMO-2026-002",
                        accepted=True,
                        invoiced=False,
                        email="author2@example.com",
                        amount=Decimal("2200.00"),
                    ),
                ]
            )

        if not db.scalar(select(KnowledgeDocument).limit(1)):
            db.add(
                KnowledgeDocument(
                    title="编辑部财务处理SOP（演示）",
                    source="内置脱敏示例",
                    content=(
                        "经办人导入财务数据后必须完成规则校验。所有异常需要复核并记录处置依据，"
                        "之后方可提交审批。审批人与经办人职责分离，批准后才能生成正式导出文件。"
                    ),
                    created_by_id=users["admin"].id,
                )
            )
        db.commit()


if __name__ == "__main__":
    seed()
