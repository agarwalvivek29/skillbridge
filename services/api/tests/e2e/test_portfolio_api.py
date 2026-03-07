"""E2E tests for portfolio API endpoints.

Uses httpx AsyncClient with a fully in-memory SQLite database so no external
services are needed. Auth is overridden via FastAPI dependency_overrides.
Tests cover the happy path for all CRUD operations plus authorization checks.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.api.main import app
from src.infra.database import Base, GigModel, GigStatus, PortfolioItemModel, get_session
from src.middleware.auth import require_auth

# Use in-memory SQLite for isolation — no external DB required
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

OWNER_USER_ID = "00000000-0000-0000-0000-000000000001"
ATTACKER_USER_ID = "00000000-0000-0000-0000-000000000099"


def _auth_as(user_id: str):
    """Return a FastAPI dependency override that authenticates as user_id."""

    async def _override() -> dict:  # type: ignore[type-arg]
        return {"subject": user_id, "method": "jwt"}

    return _override


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client with overridden DB session, authenticated as OWNER_USER_ID."""

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[require_auth] = _auth_as(OWNER_USER_ID)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# --- Happy path tests ---------------------------------------------------------


@pytest.mark.asyncio
async def test_create_portfolio_item_happy_path(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/portfolio",
        json={
            "title": "My Awesome Project",
            "description": "A full-stack web app",
            "file_keys": ["portfolio/img.png"],
            "external_url": "https://github.com/user/project",
            "tags": ["python", "fastapi"],
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "My Awesome Project"
    assert data["user_id"] == OWNER_USER_ID
    assert data["is_verified"] is False
    assert data["verified_gig_id"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_get_portfolio_items_for_user(client: AsyncClient, db_session: AsyncSession) -> None:
    for i in range(2):
        item = PortfolioItemModel(
            user_id=OWNER_USER_ID,
            title=f"Project {i}",
            description="",
            file_keys=[],
            external_url="",
            tags=[],
        )
        db_session.add(item)
    await db_session.commit()

    response = await client.get(f"/v1/portfolio?user_id={OWNER_USER_ID}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_update_portfolio_item_by_owner(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    item = PortfolioItemModel(
        user_id=OWNER_USER_ID,
        title="Original Title",
        description="",
        file_keys=[],
        external_url="",
        tags=[],
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    response = await client.put(
        f"/v1/portfolio/{item.id}",
        json={
            "title": "Updated Title",
            "description": "Updated description",
            "file_keys": [],
            "external_url": "",
            "tags": ["updated"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["tags"] == ["updated"]


@pytest.mark.asyncio
async def test_delete_portfolio_item_by_owner(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    item = PortfolioItemModel(
        user_id=OWNER_USER_ID,
        title="To Be Deleted",
        description="",
        file_keys=[],
        external_url="",
        tags=[],
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    item_id = item.id

    response = await client.delete(f"/v1/portfolio/{item_id}")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == item_id


# --- Authorization tests -------------------------------------------------------


@pytest.mark.asyncio
async def test_update_portfolio_item_forbidden_for_non_owner(
    db_session: AsyncSession,
) -> None:
    """Attacker tries to update an item owned by OWNER_USER_ID."""

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    item = PortfolioItemModel(
        user_id=OWNER_USER_ID,
        title="Owner Project",
        description="",
        file_keys=[],
        external_url="",
        tags=[],
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    item_id = item.id

    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[require_auth] = _auth_as(ATTACKER_USER_ID)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as attacker_client:
        response = await attacker_client.put(
            f"/v1/portfolio/{item_id}",
            json={
                "title": "Hacked",
                "description": "",
                "file_keys": [],
                "external_url": "",
                "tags": [],
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403, response.text


@pytest.mark.asyncio
async def test_portfolio_endpoints_require_auth(db_session: AsyncSession) -> None:
    """Without auth override, endpoints return 401 (no token provided)."""

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as unauthenticated_client:
        for method, path in [
            ("post", "/v1/portfolio"),
            ("get", "/v1/portfolio?user_id=some-user"),
            ("put", "/v1/portfolio/some-id"),
            ("delete", "/v1/portfolio/some-id"),
        ]:
            response = await getattr(unauthenticated_client, method)(path)
            assert response.status_code == 401, f"{method.upper()} {path} expected 401"

    app.dependency_overrides.clear()


# --- Badge verification test ---------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_item_verified_badge(client: AsyncClient, db_session: AsyncSession) -> None:
    gig = GigModel(status=GigStatus.GIG_STATUS_COMPLETED)
    db_session.add(gig)
    await db_session.commit()
    await db_session.refresh(gig)
    gig_id = gig.id

    response = await client.post(
        "/v1/portfolio",
        json={
            "title": "Verified Work",
            "description": "Completed on-chain",
            "file_keys": [],
            "external_url": "",
            "tags": [],
            "verified_gig_id": gig_id,
        },
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["is_verified"] is True
    assert data["verified_gig_id"] == gig_id
