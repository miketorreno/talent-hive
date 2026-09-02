from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import cast

from domain.company import Company, raise_one_company_per_owner_when
from redis import asyncio as aioredis

_COMPANY_KEY = "th:company:{id}"
_COMPANY_BY_OWNER_KEY = "th:company_by_owner:{owner_id}"
_COMPANY_MEMBERS_KEY = "th:company_members:{company_id}"
_COMPANY_BY_MEMBER_KEY = "th:company_by_member:{user_id}"


class CompanyRepository(ABC):
    """Persist companies and the owner/member -> company mappings."""

    @abstractmethod
    async def get(self, company_id: str) -> Company | None: ...

    @abstractmethod
    async def find_by_owner(self, owner_id: int) -> Company | None: ...

    @abstractmethod
    async def find_by_member(self, user_id: int) -> Company | None: ...

    @abstractmethod
    async def save(self, company: Company) -> None: ...

    @abstractmethod
    async def delete(self, company_id: str) -> None: ...


class RedisCompanyRepository(CompanyRepository):
    """Redis-backed company repository: one JSON string per company."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, company_id: str) -> Company | None:
        raw = await self._redis.get(_COMPANY_KEY.format(id=company_id))  # type: ignore[misc]
        return _decode_company(raw)

    async def find_by_owner(self, owner_id: int) -> Company | None:
        company_id = await self._company_id_for_owner(owner_id)
        if company_id is None:
            return None
        return await self.get(company_id)

    async def find_by_member(self, user_id: int) -> Company | None:
        raw = await self._redis.get(  # type: ignore[misc]
            _COMPANY_BY_MEMBER_KEY.format(user_id=user_id)
        )
        if raw is None:
            return None
        company_id = raw.decode() if isinstance(raw, bytes) else raw
        return await self.get(company_id)

    async def save(self, company: Company) -> None:
        if company.owner_id is not None:
            await self._enforce_one_company_per_owner(company)
        await self._redis.set(  # type: ignore[misc]
            _COMPANY_KEY.format(id=company.id), _encode_company(company)
        )
        if company.owner_id is not None:
            await self._redis.set(  # type: ignore[misc]
                _COMPANY_BY_OWNER_KEY.format(owner_id=company.owner_id),
                company.id,
            )
        await self._sync_members(company)

    async def _enforce_one_company_per_owner(self, company: Company) -> None:
        existing_id = await self._company_id_for_owner(company.owner_id)
        raise_one_company_per_owner_when(
            existing_id is not None and existing_id != company.id
        )

    async def _company_id_for_owner(self, owner_id: int | None) -> str | None:
        if owner_id is None:
            return None
        raw = await self._redis.get(  # type: ignore[misc]
            _COMPANY_BY_OWNER_KEY.format(owner_id=owner_id)
        )
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    async def delete(self, company_id: str) -> None:
        company = await self.get(company_id)
        if company is not None:
            if company.owner_id is not None:
                await self._redis.delete(  # type: ignore[misc]
                    _COMPANY_BY_OWNER_KEY.format(owner_id=company.owner_id)
                )
            await self._clear_member_indexes(company)
        await self._redis.delete(_COMPANY_KEY.format(id=company_id))  # type: ignore[misc]

    async def _sync_members(self, company: Company) -> None:
        member_key = _COMPANY_MEMBERS_KEY.format(company_id=company.id)
        old_members = cast(
            "set[bytes]",
            await self._redis.smembers(member_key),  # type: ignore[misc]
        )
        old_ids = {int(m.decode()) for m in old_members}
        new_ids = company.members()
        for member_id in old_ids - new_ids:
            await self._redis.delete(  # type: ignore[misc]
                _COMPANY_BY_MEMBER_KEY.format(user_id=member_id)
            )
        for member_id in new_ids:
            await self._redis.set(  # type: ignore[misc]
                _COMPANY_BY_MEMBER_KEY.format(user_id=member_id),
                company.id,
            )
        if new_ids:
            await self._redis.sadd(  # type: ignore[misc]
                member_key, *[str(m) for m in new_ids]
            )
        else:
            await self._redis.delete(member_key)  # type: ignore[misc]

    async def _clear_member_indexes(self, company: Company) -> None:
        member_key = _COMPANY_MEMBERS_KEY.format(company_id=company.id)
        members = cast(
            "set[bytes]",
            await self._redis.smembers(member_key),  # type: ignore[misc]
        )
        for member in members:
            await self._redis.delete(  # type: ignore[misc]
                _COMPANY_BY_MEMBER_KEY.format(user_id=int(member.decode()))
            )
        await self._redis.delete(member_key)  # type: ignore[misc]


def _encode_company(company: Company) -> str:
    data = {
        "id": company.id,
        "name": company.name,
        "description": company.description,
        "owner_id": company.owner_id,
        "recruiter_ids": sorted(company.recruiter_ids),
    }
    return json.dumps(data)


def _decode_company(raw: bytes | str | None) -> Company | None:
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    data = json.loads(raw)
    return Company(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        owner_id=data["owner_id"],
        recruiter_ids=set(data["recruiter_ids"]),
    )
