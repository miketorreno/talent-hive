from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import cast

from domain.application import Application, ApplicationStatus
from redis import asyncio as aioredis

_APPLICATION_KEY = "th:application:{id}"
_APPLICATIONS_BY_JOB_KEY = "th:applications_by_job:{job_id}"
_APPLICATIONS_BY_SEEKER_KEY = "th:applications_by_seeker:{seeker_id}"


class ApplicationRepository(ABC):
    """Persist applications and index them by job and by seeker."""

    @abstractmethod
    async def get(self, application_id: str) -> Application | None: ...

    @abstractmethod
    async def list_by_job(self, job_id: str) -> list[Application]: ...

    @abstractmethod
    async def list_by_seeker(self, seeker_id: int) -> list[Application]: ...

    @abstractmethod
    async def save(self, application: Application) -> None: ...


class RedisApplicationRepository(ApplicationRepository):
    """Redis-backed application repository: one JSON string per application."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, application_id: str) -> Application | None:
        raw = await self._redis.get(_APPLICATION_KEY.format(id=application_id))  # type: ignore[misc]
        return _decode_application(raw)

    async def list_by_job(self, job_id: str) -> list[Application]:
        ids = await self._smembers(_APPLICATIONS_BY_JOB_KEY.format(job_id=job_id))
        applications = [await self.get(app_id) for app_id in ids]
        return [app for app in applications if app is not None]

    async def list_by_seeker(self, seeker_id: int) -> list[Application]:
        ids = await self._smembers(
            _APPLICATIONS_BY_SEEKER_KEY.format(seeker_id=seeker_id)
        )
        applications = [await self.get(app_id) for app_id in ids]
        return [app for app in applications if app is not None]

    async def save(self, application: Application) -> None:
        await self._redis.set(  # type: ignore[misc]
            _APPLICATION_KEY.format(id=application.id), _encode_application(application)
        )
        await self._redis.sadd(  # type: ignore[misc]
            _APPLICATIONS_BY_JOB_KEY.format(job_id=application.job_id), application.id
        )
        await self._redis.sadd(  # type: ignore[misc]
            _APPLICATIONS_BY_SEEKER_KEY.format(seeker_id=application.seeker_id),
            application.id,
        )

    async def _smembers(self, key: str) -> set[str]:
        members = cast(
            "set[bytes]",
            await self._redis.smembers(key),  # type: ignore[misc]
        )
        return {member.decode() for member in members}


def _encode_application(application: Application) -> str:
    data = {
        "id": application.id,
        "job_id": application.job_id,
        "seeker_id": application.seeker_id,
        "status": application.status.value,
        "cover_letter": application.cover_letter,
        "created_at": application.created_at.isoformat(),
    }
    return json.dumps(data)


def _decode_application(raw: bytes | str | None) -> Application | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    data = json.loads(raw)
    return Application(
        id=data["id"],
        job_id=data["job_id"],
        seeker_id=data["seeker_id"],
        status=ApplicationStatus(data["status"]),
        cover_letter=data["cover_letter"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )
