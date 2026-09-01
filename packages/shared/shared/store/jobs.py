from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import cast

from domain.job import Job, JobStatus
from redis import asyncio as aioredis

_JOB_KEY = "th:job:{id}"
_JOBS_BY_COMPANY_KEY = "th:jobs_by_company:{company_id}"


class JobRepository(ABC):
    """Persist jobs and index them by company."""

    @abstractmethod
    async def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    async def list_by_company(self, company_id: str) -> list[Job]: ...

    @abstractmethod
    async def save(self, job: Job) -> None: ...

    @abstractmethod
    async def delete(self, job_id: str) -> None: ...


class RedisJobRepository(JobRepository):
    """Redis-backed job repository: one JSON string per job."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, job_id: str) -> Job | None:
        raw = await self._redis.get(_JOB_KEY.format(id=job_id))  # type: ignore[misc]
        return _decode_job(raw)

    async def list_by_company(self, company_id: str) -> list[Job]:
        ids = cast(
            "set[bytes]",
            await self._redis.smembers(  # type: ignore[misc]
                _JOBS_BY_COMPANY_KEY.format(company_id=company_id)
            ),
        )
        jobs = [await self.get(job_id.decode()) for job_id in ids]
        return [job for job in jobs if job is not None]

    async def save(self, job: Job) -> None:
        await self._redis.set(  # type: ignore[misc]
            _JOB_KEY.format(id=job.id), _encode_job(job)
        )
        await self._redis.sadd(  # type: ignore[misc]
            _JOBS_BY_COMPANY_KEY.format(company_id=job.company_id), job.id
        )

    async def delete(self, job_id: str) -> None:
        job = await self.get(job_id)
        if job is not None:
            await self._redis.srem(  # type: ignore[misc]
                _JOBS_BY_COMPANY_KEY.format(company_id=job.company_id), job.id
            )
        await self._redis.delete(_JOB_KEY.format(id=job_id))  # type: ignore[misc]


def _encode_job(job: Job) -> str:
    data = {
        "id": job.id,
        "company_id": job.company_id,
        "title": job.title,
        "description": job.description,
        "requirements": job.requirements,
        "created_by": job.created_by,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "expires_at": job.expires_at.isoformat() if job.expires_at else None,
    }
    return json.dumps(data)


def _decode_job(raw: bytes | str | None) -> Job | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    data = json.loads(raw)
    return Job(
        id=data["id"],
        company_id=data["company_id"],
        title=data["title"],
        description=data["description"],
        requirements=data["requirements"],
        created_by=data["created_by"],
        status=JobStatus(data["status"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        expires_at=(
            datetime.fromisoformat(data["expires_at"])
            if data["expires_at"]
            else None
        ),
    )
