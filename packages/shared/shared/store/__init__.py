"""Talent Hive store: persistence abstractions for entities.

These repositories are thin I/O shells over Redis/Postgres. Behavioral rules
live in the `domain` package, so the shells only map to/from domain objects.
"""

from .users import RedisUserRepository, UserRepository

__all__ = ["UserRepository", "RedisUserRepository"]
