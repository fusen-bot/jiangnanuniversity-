from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.enums import RoleCode
from app.main import app
from app.models import Role, User
from app.security import hash_password


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def users(db: Session) -> dict[str, User]:
    result: dict[str, User] = {}
    for code in RoleCode:
        role = Role(code=code.value, name=code.value)
        user = User(
            username=code.value,
            display_name=code.value,
            password_hash=hash_password(f"{code.value.title()}123!"),
            roles=[role],
        )
        db.add_all([role, user])
        result[code.value] = user
    db.commit()
    return result


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
