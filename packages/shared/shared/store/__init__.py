"""Talent Hive store: persistence abstractions for entities.

These repositories are thin I/O shells over Redis/Postgres. Behavioral rules
live in the `domain` package, so the shells only map to/from domain objects.
"""

from dataclasses import dataclass

from redis import asyncio as aioredis

from .applications import (
    ApplicationRepository,
    RedisApplicationRepository,
)
from .artifacts import ArtifactRepository, RedisArtifactRepository
from .companies import CompanyRepository, RedisCompanyRepository
from .jobs import JobRepository, RedisJobRepository
from .profiles import RedisSeekerProfileRepository, SeekerProfileRepository
from .users import RedisUserRepository, UserRepository


@dataclass
class Store:
    """The aggregate of repositories the bot talks to."""

    users: UserRepository
    companies: CompanyRepository
    jobs: JobRepository
    profiles: SeekerProfileRepository
    applications: ApplicationRepository
    artifacts: ArtifactRepository


def build_store(redis_url: str) -> Store:
    """Build a Store wired to a real Redis URL."""
    redis = aioredis.from_url(redis_url, decode_responses=False)
    return Store(
        users=RedisUserRepository(redis),
        companies=RedisCompanyRepository(redis),
        jobs=RedisJobRepository(redis),
        profiles=RedisSeekerProfileRepository(redis),
        applications=RedisApplicationRepository(redis),
        artifacts=RedisArtifactRepository(redis),
    )


__all__ = [
    "Store",
    "build_store",
    "UserRepository",
    "RedisUserRepository",
    "CompanyRepository",
    "RedisCompanyRepository",
    "JobRepository",
    "RedisJobRepository",
    "SeekerProfileRepository",
    "RedisSeekerProfileRepository",
    "ApplicationRepository",
    "RedisApplicationRepository",
    "ArtifactRepository",
    "RedisArtifactRepository",
]
