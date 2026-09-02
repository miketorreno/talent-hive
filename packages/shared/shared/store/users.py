from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

from domain.identities import Role, User
from redis import asyncio as aioredis

_USER_KEY = "th:user:{telegram_id}"


class UserRepository(ABC):
    """Persist an identity's roles keyed by Telegram user ID."""

    @abstractmethod
    async def get(self, telegram_id: int) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...


class RedisUserRepository(UserRepository):
    """Redis-backed user repository: roles stored as a set per user."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, telegram_id: int) -> User | None:
        roles = cast(
            "set[bytes]",
            await self._redis.smembers(  # type: ignore[misc]
                _USER_KEY.format(telegram_id=telegram_id)
            ),
        )
        if not roles:
            return None
        role_set = frozenset(Role(role.decode()) for role in roles)
        return User(telegram_id=telegram_id, roles=role_set)

    async def save(self, user: User) -> None:
        key = _USER_KEY.format(telegram_id=user.telegram_id)
        if user.roles:
            await self._redis.sadd(  # type: ignore[misc]
                key, *[role.value for role in user.roles]
            )
        else:
            await self._redis.delete(key)  # type: ignore[misc]
