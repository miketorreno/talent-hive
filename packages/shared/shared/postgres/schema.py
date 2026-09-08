from __future__ import annotations

from pathlib import Path

import asyncpg

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def load_schema() -> str:
    """Return the DDL for the Talent Hive Postgres data model."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


async def apply_schema(conn: asyncpg.Connection) -> None:
    """Apply the schema to a Postgres connection, idempotently.

    Every statement in ``schema.sql`` is guarded (CREATE ... IF NOT EXISTS and
    DO-block enum creation), so calling this repeatedly over an existing
    database is safe.
    """
    await conn.execute(load_schema())
