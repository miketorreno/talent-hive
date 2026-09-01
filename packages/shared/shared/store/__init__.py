"""Talent Hive store: persistence abstractions for entities.

These repositories are thin I/O shells over Redis/Postgres. Behavioral rules
live in the `domain` package, so the shells only map to/from domain objects.
"""

from dataclasses import dataclass

from .companies import CompanyRepository, RedisCompanyRepository
from .jobs import JobRepository, RedisJobRepository
from .users import RedisUserRepository, UserRepository


@dataclass
class Store:
    """The aggregate of repositories the bot talks to."""

    users: UserRepository
    companies: CompanyRepository
    jobs: JobRepository


__all__ = [
    "Store",
    "UserRepository",
    "RedisUserRepository",
    "CompanyRepository",
    "RedisCompanyRepository",
    "JobRepository",
    "RedisJobRepository",
]
