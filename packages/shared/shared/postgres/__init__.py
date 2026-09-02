"""Postgres persistence: schema and repository shells.

Repositories map rows to/from `domain` objects. All behavioral rules live in
the `domain` package; these shells only shape SQL around those objects (see
docs/adr/0001). The schema is defined in ``schema.sql``.
"""

from .repositories import (
    PostgresApplicationRepository,
    PostgresArtifactRepository,
    PostgresCompanyRepository,
    PostgresJobRepository,
    PostgresSeekerProfileRepository,
    PostgresStore,
    PostgresUserRepository,
)
from .schema import apply_schema, load_schema

__all__ = [
    "PostgresStore",
    "PostgresUserRepository",
    "PostgresCompanyRepository",
    "PostgresJobRepository",
    "PostgresSeekerProfileRepository",
    "PostgresApplicationRepository",
    "PostgresArtifactRepository",
    "apply_schema",
    "load_schema",
]
