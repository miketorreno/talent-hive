import builtins

from domain.identities import Role, User
from shared.store import (
    RedisApplicationRepository,
    RedisCompanyRepository,
    RedisJobRepository,
    RedisSeekerProfileRepository,
    RedisUserRepository,
    Store,
)

Set = builtins.set


class FakeRedis:
    """In-memory stand-in for the redis commands the repositories use."""

    def __init__(self) -> None:
        self._strings: dict[str, str] = {}
        self._sets: dict[str, Set[bytes]] = {}

    async def get(self, key: str) -> str | None:
        return self._strings.get(key)

    async def set(self, key: str, value: str) -> None:
        self._strings[key] = value

    async def delete(self, key: str) -> int:
        existed = key in self._strings
        self._strings.pop(key, None)
        return 1 if existed else 0

    async def smembers(self, key: str) -> Set[bytes]:
        return Set(self._sets.get(key, Set()))

    async def sadd(self, key: str, *values: str) -> int:
        self._sets.setdefault(key, Set()).update(v.encode() for v in values)
        return len(values)

    async def srem(self, key: str, *removals: str) -> int:
        bucket = self._sets.get(key, Set())
        removed = 0
        for v in removals:
            if v.encode() in bucket:
                bucket.remove(v.encode())
                removed += 1
        return removed

    async def smismember(self, key: str, *members: str) -> list[int]:
        bucket = self._sets.get(key, Set())
        return [1 if m.encode() in bucket else 0 for m in members]


class FakeChat:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send_message(self, text: str, **_: object) -> None:
        self.messages.append(text)


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeUpdate:
    def __init__(self, user_id: int) -> None:
        self.effective_user = FakeUser(user_id)
        self.effective_chat = FakeChat()
        self.callback_query = None


class FakeContext:
    def __init__(self, store: Store, args: list[str] | None = None) -> None:
        self.bot_data: dict[str, object] = {"store": store}
        self.args = args or []


def make_store() -> Store:
    redis = FakeRedis()
    return Store(
        users=RedisUserRepository(redis),  # type: ignore[arg-type]
        companies=RedisCompanyRepository(redis),  # type: ignore[arg-type]
        jobs=RedisJobRepository(redis),  # type: ignore[arg-type]
        profiles=RedisSeekerProfileRepository(redis),  # type: ignore[arg-type]
        applications=RedisApplicationRepository(redis),  # type: ignore[arg-type]
    )


async def register(store: Store, user_id: int, role: Role) -> None:
    await store.users.save(
        User(telegram_id=user_id, roles=frozenset({role}))
    )


async def register_seeker(store: Store, user_id: int) -> None:
    await register(store, user_id, Role.JOB_SEEKER)


async def register_employer(store: Store, user_id: int) -> None:
    await register(store, user_id, Role.EMPLOYER)
