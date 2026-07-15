import json

import httpx

from conditioner.core.adapters.persistence.d1.client import D1Client


def _handler(expected_body: object) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content) == expected_body
        assert request.url.path == "/client/v4/accounts/acct-1/d1/database/db-1/query"
        assert request.headers["authorization"] == "Bearer token-1"
        return httpx.Response(200, json={"result": [{"results": [{"id": "1"}]}], "success": True})

    return httpx.MockTransport(handle)


async def test_query_sends_single_statement_and_returns_results() -> None:
    transport = _handler({"sql": "SELECT * FROM users WHERE id = ?", "params": ["1"]})
    client = D1Client("acct-1", "db-1", "token-1", transport=transport)

    rows = await client.query("SELECT * FROM users WHERE id = ?", ("1",))

    assert rows == [{"id": "1"}]


async def test_batch_sends_statements_as_array() -> None:
    transport = _handler(
        [
            {"sql": "INSERT INTO users (id) VALUES (?)", "params": ["1"]},
            {"sql": "DELETE FROM sessions WHERE user_id = ?", "params": ["1"]},
        ]
    )
    client = D1Client("acct-1", "db-1", "token-1", transport=transport)

    await client.batch(
        [
            ("INSERT INTO users (id) VALUES (?)", ("1",)),
            ("DELETE FROM sessions WHERE user_id = ?", ("1",)),
        ]
    )
