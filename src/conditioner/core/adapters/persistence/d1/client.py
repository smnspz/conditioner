from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from conditioner.shared.constants import Constants

JsonRow = dict[str, Any]


class D1Client:
    """Thin wrapper over the Cloudflare D1 REST API (query + batch endpoints)."""

    def __init__(
        self,
        account_id: str,
        database_id: str,
        api_token: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # Initializations
        self._url = (
            f"{Constants.cloudflare_api_base_url()}"
            f"/accounts/{account_id}/d1/database/{database_id}/query"
        )
        self._headers = {"Authorization": f"Bearer {api_token}"}
        self._transport = transport

    async def query(self, sql: str, params: Sequence[Any] = ()) -> list[JsonRow]:
        """Run a single statement and return its result rows."""

        # Get the single statement's result set
        results = await self._post({"sql": sql, "params": list(params)})
        return results[0]["results"]  # type: ignore[no-any-return]

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        """Run a single write statement, discarding any result rows."""

        await self._post({"sql": sql, "params": list(params)})

    async def batch(self, statements: Sequence[tuple[str, Sequence[Any]]]) -> None:
        """Run multiple statements as a single atomic transaction."""

        await self._post([{"sql": sql, "params": list(params)} for sql, params in statements])

    async def _post(self, body: JsonRow | list[JsonRow]) -> list[JsonRow]:
        """Post a query/batch payload and return D1's per-statement result list."""

        async with httpx.AsyncClient(transport=self._transport) as client:
            # Get the raw HTTP response from the D1 query endpoint
            response = await client.post(self._url, headers=self._headers, json=body)
            response.raise_for_status()

        # Return the per-statement result list
        return response.json()["result"]  # type: ignore[no-any-return]
