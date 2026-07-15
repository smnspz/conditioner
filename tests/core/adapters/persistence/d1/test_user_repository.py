from datetime import UTC, datetime

import httpx

from conditioner.core.adapters.persistence.d1.client import D1Client
from conditioner.core.adapters.persistence.d1.user_repository import D1UserRepository
from conditioner.core.domain.auth.user import User

_USER_ROW = {
    "id": "user-1",
    "email": "athlete@example.com",
    "created_at": "2026-01-01T00:00:00+00:00",
    "consent_given_at": "2026-01-02T00:00:00+00:00",
}


def _client(handle: httpx.MockTransport | None = None) -> D1Client:
    return D1Client("acct-1", "db-1", "token-1", transport=handle)


async def test_get_by_id_maps_row_to_domain() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": [{"results": [_USER_ROW]}], "success": True})

    repo = D1UserRepository(_client(httpx.MockTransport(handle)))

    fetched = await repo.get_by_id("user-1")

    assert fetched == User(
        id="user-1",
        email="athlete@example.com",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        consent_given_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


async def test_get_by_id_returns_none_when_missing() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": [{"results": []}], "success": True})

    repo = D1UserRepository(_client(httpx.MockTransport(handle)))

    assert await repo.get_by_id("missing") is None


async def test_save_sends_upsert_statement() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        assert "INSERT INTO users" in body
        assert "user-1" in body
        return httpx.Response(200, json={"result": [{"results": []}], "success": True})

    repo = D1UserRepository(_client(httpx.MockTransport(handle)))

    await repo.save(
        User(id="user-1", email="athlete@example.com", created_at=datetime.now(UTC))
    )
