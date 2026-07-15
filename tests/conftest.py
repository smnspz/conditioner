from collections.abc import Iterator
from pathlib import Path

import pytest
from yoyo import get_backend, read_migrations

MIGRATIONS_DIR = Path(__file__).parents[1] / "migrations" / "sqlite"


@pytest.fixture
def db_path(tmp_path: Path) -> Iterator[str]:
    path = tmp_path / "conditioner.db"
    backend = get_backend(f"sqlite:///{path}")
    migrations = read_migrations(str(MIGRATIONS_DIR))
    with backend.lock():
        backend.apply_migrations(migrations)
    yield str(path)
