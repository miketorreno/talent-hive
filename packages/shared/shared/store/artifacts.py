from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import cast

from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from redis import asyncio as aioredis

_ARTIFACT_KEY = "th:artifact:{id}"
_ARTIFACTS_BY_OWNER_KEY = "th:artifacts_by_owner:{owner_id}"


class ArtifactRepository(ABC):
    """Persist artifacts and index them by owner."""

    @abstractmethod
    async def get(self, artifact_id: str) -> Artifact | None: ...

    @abstractmethod
    async def list_by_owner(
        self, owner_id: int, type: ArtifactType | None = None
    ) -> list[Artifact]: ...

    @abstractmethod
    async def save(self, artifact: Artifact) -> None: ...


class RedisArtifactRepository(ArtifactRepository):
    """Redis-backed artifact repository: one JSON string per artifact."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, artifact_id: str) -> Artifact | None:
        raw = await self._redis.get(_ARTIFACT_KEY.format(id=artifact_id))  # type: ignore[misc]
        return _decode_artifact(raw)

    async def list_by_owner(
        self, owner_id: int, type: ArtifactType | None = None
    ) -> list[Artifact]:
        ids = await self._smembers(
            _ARTIFACTS_BY_OWNER_KEY.format(owner_id=owner_id)
        )
        artifacts: list[Artifact] = []
        for artifact_id in ids:
            artifact = await self.get(artifact_id)
            if artifact is None:
                continue
            if type is not None and artifact.type != type:
                continue
            artifacts.append(artifact)
        return artifacts

    async def save(self, artifact: Artifact) -> None:
        await self._redis.set(  # type: ignore[misc]
            _ARTIFACT_KEY.format(id=artifact.id), _encode_artifact(artifact)
        )
        await self._redis.sadd(  # type: ignore[misc]
            _ARTIFACTS_BY_OWNER_KEY.format(owner_id=artifact.owner_id), artifact.id
        )

    async def _smembers(self, key: str) -> set[str]:
        members = cast(
            "set[bytes]",
            await self._redis.smembers(key),  # type: ignore[misc]
        )
        return {member.decode() for member in members}


def _encode_artifact(artifact: Artifact) -> str:
    data = {
        "id": artifact.id,
        "type": artifact.type.value,
        "owner_id": artifact.owner_id,
        "origin": artifact.origin.value,
        "text": artifact.text,
        "storage_key": artifact.storage_key,
        "created_at": artifact.created_at.isoformat(),
    }
    return json.dumps(data)


def _decode_artifact(raw: bytes | str | None) -> Artifact | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    data = json.loads(raw)
    return Artifact(
        id=data["id"],
        type=ArtifactType(data["type"]),
        owner_id=data["owner_id"],
        origin=ArtifactOrigin(data["origin"]),
        text=data["text"],
        storage_key=data["storage_key"],
        created_at=datetime.fromisoformat(data["created_at"]),
    )
