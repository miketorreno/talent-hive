import pytest
from domain.identities import Role, User
from shared.store import RedisUserRepository


class FakeRedis:
    """Minimal in-memory stand-in for the redis set commands the repo uses."""

    def __init__(self) -> None:
        self._data: dict[str, set[bytes]] = {}

    async def smembers(self, key: str) -> set[bytes]:
        return set(self._data.get(key, set()))

    async def sadd(self, key: str, *values: str) -> int:
        self._data.setdefault(key, set()).update(v.encode() for v in values)
        return len(values)

    async def delete(self, key: str) -> int:
        existed = key in self._data
        self._data.pop(key, None)
        return 1 if existed else 0


@pytest.fixture
def repo() -> RedisUserRepository:
    return RedisUserRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_unknown_user_is_none(repo: RedisUserRepository) -> None:
    assert await repo.get(999) is None


@pytest.mark.asyncio
async def test_save_and_get_roundtrip_single_role(repo: RedisUserRepository) -> None:
    await repo.save(User(telegram_id=1, roles=frozenset({Role.EMPLOYER})))
    loaded = await repo.get(1)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.EMPLOYER})


@pytest.mark.asyncio
async def test_save_and_get_roundtrip_both_roles(repo: RedisUserRepository) -> None:
    roles = frozenset({Role.EMPLOYER, Role.JOB_SEEKER})
    await repo.save(User(telegram_id=2, roles=roles))
    loaded = await repo.get(2)
    assert loaded is not None
    assert loaded.roles == roles


@pytest.mark.asyncio
async def test_save_empty_roles_clears(repo: RedisUserRepository) -> None:
    await repo.save(User(telegram_id=3, roles=frozenset({Role.JOB_SEEKER})))
    await repo.save(User(telegram_id=3, roles=frozenset()))
    assert await repo.get(3) is None
