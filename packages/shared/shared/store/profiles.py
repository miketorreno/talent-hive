from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime

from domain.profile import SeekerProfile
from redis import asyncio as aioredis

_PROFILE_KEY = "th:profile:{seeker_id}"


class SeekerProfileRepository(ABC):
    """Persist a job seeker's Seeker Profile."""

    @abstractmethod
    async def get(self, seeker_id: int) -> SeekerProfile | None: ...

    @abstractmethod
    async def save(self, profile: SeekerProfile) -> None: ...


class RedisSeekerProfileRepository(SeekerProfileRepository):
    """Redis-backed profile repository: one JSON string per seeker."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, seeker_id: int) -> SeekerProfile | None:
        raw = await self._redis.get(_PROFILE_KEY.format(seeker_id=seeker_id))  # type: ignore[misc]
        return _decode_profile(raw)

    async def save(self, profile: SeekerProfile) -> None:
        await self._redis.set(  # type: ignore[misc]
            _PROFILE_KEY.format(seeker_id=profile.seeker_id), _encode_profile(profile)
        )


def _encode_profile(profile: SeekerProfile) -> str:
    data = {
        "seeker_id": profile.seeker_id,
        "skills": profile.skills,
        "experience": profile.experience,
        "background": profile.background,
        "updated_at": profile.updated_at.isoformat(),
    }
    return json.dumps(data)


def _decode_profile(raw: bytes | str | None) -> SeekerProfile | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    data = json.loads(raw)
    return SeekerProfile(
        seeker_id=data["seeker_id"],
        skills=data["skills"],
        experience=data["experience"],
        background=data["background"],
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )
