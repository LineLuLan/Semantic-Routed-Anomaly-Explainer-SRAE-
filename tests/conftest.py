"""Shared pytest fixtures.

If the database is unreachable we skip DB-backed tests rather than fail,
so contributors can run unit tests without Postgres running.
"""

from __future__ import annotations

import pytest

from src.db.connection import ping


@pytest.fixture(scope="session")
def db_available() -> bool:
    return ping()


@pytest.fixture(autouse=True)
def _skip_if_db_required(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("requires_db")
    if marker is None:
        return
    if not ping():
        pytest.skip("Postgres is not reachable; set POSTGRES_URL and start the server.")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_db: test needs a live Postgres with schema applied",
    )
