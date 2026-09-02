import builtins

from domain.identities import Role, User
from shared.store import (
    RedisApplicationRepository,
    RedisArtifactRepository,
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
        self.documents: list[str] = []

    async def send_message(self, text: str, **_: object) -> None:
        self.messages.append(text)

    async def send_document(self, document: str, **_: object) -> None:
        self.documents.append(document)


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeDocument:
    def __init__(self, file_id: str) -> None:
        self.file_id = file_id


class FakeMessage:
    def __init__(self, document: FakeDocument | None = None) -> None:
        self.document = document


class FakeUpdate:
    def __init__(
        self, user_id: int, document: FakeDocument | None = None
    ) -> None:
        self.effective_user = FakeUser(user_id)
        self.effective_chat = FakeChat()
        self.callback_query = None
        self.message = FakeMessage(document)


class FakeArq:
    """In-memory stand-in for the arq pool used by the bot to enqueue jobs."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def enqueue_job(
        self,
        name: str,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.jobs.append((name, args, kwargs))


class FakeContext:
    def __init__(
        self,
        store: Store,
        args: list[str] | None = None,
        arq: FakeArq | None = None,
    ) -> None:
        self.bot_data: dict[str, object] = {"store": store}
        if arq is not None:
            self.bot_data["arq"] = arq
        self.args = args or []


def make_store() -> Store:
    redis = FakeRedis()
    return Store(
        users=RedisUserRepository(redis),  # type: ignore[arg-type]
        companies=RedisCompanyRepository(redis),  # type: ignore[arg-type]
        jobs=RedisJobRepository(redis),  # type: ignore[arg-type]
        profiles=RedisSeekerProfileRepository(redis),  # type: ignore[arg-type]
        applications=RedisApplicationRepository(redis),  # type: ignore[arg-type]
        artifacts=RedisArtifactRepository(redis),  # type: ignore[arg-type]
    )


async def register(store: Store, user_id: int, role: Role) -> None:
    await store.users.save(
        User(telegram_id=user_id, roles=frozenset({role}))
    )


async def register_seeker(store: Store, user_id: int) -> None:
    await register(store, user_id, Role.JOB_SEEKER)


async def register_employer(store: Store, user_id: int) -> None:
    await register(store, user_id, Role.EMPLOYER)
