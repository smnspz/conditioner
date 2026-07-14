from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite


@asynccontextmanager
async def connect(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    """Open a SQLite connection with row access by column name and FK enforcement."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn
