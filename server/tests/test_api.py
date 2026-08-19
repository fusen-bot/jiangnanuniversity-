from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.enums import BatchStatus, BusinessType
from app.models import ProcessingBatch, User


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return client.cookies["csrf_token"]


def test_login_csrf_and_role_boundary(client: TestClient, users: dict[str, User]):
    del users
    csrf = login(client, "viewer", "Viewer123!")
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/audit-events").status_code == 403
    blocked = client.post("/api/v1/auth/logout")
    assert blocked.status_code == 403
    allowed = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert allowed.status_code == 204


def test_admin_can_list_users(client: TestClient, users: dict[str, User]):
    del users
    login(client, "admin", "Admin123!")
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_viewer_only_lists_approved_batches(client: TestClient, db: Session, users: dict[str, User]):
    db.add_all(
        [
            ProcessingBatch(
                name="未批准",
                business_type=BusinessType.REVIEW_FEE,
                status=BatchStatus.PENDING_REVIEW,
                created_by_id=users["operator"].id,
            ),
            ProcessingBatch(
                name="已批准",
                business_type=BusinessType.REVIEW_FEE,
                status=BatchStatus.APPROVED,
                created_by_id=users["operator"].id,
            ),
        ]
    )
    db.commit()
    login(client, "viewer", "Viewer123!")
    response = client.get("/api/v1/batches")
    assert response.status_code == 200
    assert [batch["name"] for batch in response.json()] == ["已批准"]


def test_creator_cannot_approve_own_batch(client: TestClient, db: Session, users: dict[str, User]):
    batch = ProcessingBatch(
        name="管理员创建",
        business_type=BusinessType.PAGE_FEE,
        status=BatchStatus.PENDING_APPROVAL,
        created_by_id=users["admin"].id,
    )
    db.add(batch)
    db.commit()
    csrf = login(client, "admin", "Admin123!")
    response = client.post(
        f"/api/v1/approvals/{batch.id}",
        headers={"X-CSRF-Token": csrf},
        json={"decision": "approve", "comment": "同意"},
    )
    assert response.status_code == 409
