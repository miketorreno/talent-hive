from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio
from shared.postgres import PostgresStore
from shared.postgres.schema import apply_schema

TEST_DATABASE_URL = os.environ.get(
    "TH_TEST_DATABASE_URL", "postgresql://postgres@localhost:54329/talent_hive_test"
)


@pytest_asyncio.fixture
async def pg_store() -> AsyncGenerator[PostgresStore, None]:
    """A Postgres-backed store against a real database, isolated per test.

    Applies the schema once and truncates all Talent Hive tables before each
    test so tests are independent. Skipped when no Postgres is reachable.
    """
    try:
        conn = await asyncpg.connect(TEST_DATABASE_URL)
    except (asyncpg.PostgresError, OSError):
        import pytest

        pytest.skip("no Postgres available for integration tests")
        raise

    await apply_schema(conn)
    await _truncate_all(conn)
    store = PostgresStore(conn)
    try:
        yield store
    finally:
        await conn.close()


async def _truncate_all(conn: asyncpg.Connection) -> None:
    tables = [
        "user_roles",
        "company_recruiters",
        "applications",
        "artifacts",
        "seeker_profiles",
        "jobs",
        "companies",
        "users",
    ]
    for table in tables:
        await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
