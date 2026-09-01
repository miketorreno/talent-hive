import builtins

import pytest
from bot.employers import (
    add_recruiter,
    archive,
    close,
    company,
    new_job,
    publish,
    set_description,
    set_requirements,
)
from domain.identities import Role, User
from shared.store import (
    RedisCompanyRepository,
    RedisJobRepository,
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
    )


async def _register_employer(store: Store, user_id: int) -> None:
    await store.users.save(User(telegram_id=user_id, roles=frozenset({Role.EMPLOYER})))


async def _create_company(store: Store, owner: int, name: str) -> None:
    await _register_employer(store, owner)
    await company(FakeUpdate(owner), FakeContext(store, [name]))  # type: ignore[arg-type]


async def _create_job(store: Store, user_id: int, title: str) -> Store:
    await new_job(FakeUpdate(user_id), FakeContext(store, [title]))  # type: ignore[arg-type]
    return store


@pytest.mark.asyncio
async def test_employer_creates_company_and_becomes_owner() -> None:
    store = make_store()
    await _register_employer(store, 1)
    update = FakeUpdate(1)
    context = FakeContext(store, ["Acme"])

    await company(update, context)  # type: ignore[arg-type]

    created = await store.companies.find_by_owner(1)
    assert created is not None
    assert created.name == "Acme"
    assert "Owner" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_employer_cannot_create_second_company() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    second = FakeUpdate(1)

    await company(second, FakeContext(store, ["Globex"]))  # type: ignore[arg-type]

    created = await store.companies.find_by_owner(1)
    assert created is not None
    assert created.name == "Acme"
    assert "one company" in second.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_owner_adds_recruiter() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _register_employer(store, 9)

    update = FakeUpdate(1)
    await add_recruiter(update, FakeContext(store, ["9"]))  # type: ignore[arg-type]

    created = await store.companies.find_by_member(9)
    assert created is not None
    assert "Recruiter" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_non_owner_cannot_add_recruiter() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _register_employer(store, 9)

    update = FakeUpdate(9)
    await add_recruiter(update, FakeContext(store, ["2"]))  # type: ignore[arg-type]

    assert await store.companies.find_by_member(9) is None
    assert "Only an Owner" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_cannot_add_non_employer_as_recruiter() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")

    update = FakeUpdate(1)
    await add_recruiter(update, FakeContext(store, ["99"]))  # type: ignore[arg-type]

    assert await store.companies.find_by_member(99) is None
    assert "isn't an Employer" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_employer_creates_draft_job_and_publishes() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _create_job(store, 1, "Engineer")

    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]
    assert job.title == "Engineer"

    await set_description(FakeUpdate(1), FakeContext(store, [job.id, "Build things"]))  # type: ignore[arg-type]
    await set_requirements(FakeUpdate(1), FakeContext(store, [job.id, "Python"]))  # type: ignore[arg-type]

    pub = FakeUpdate(1)
    await publish(pub, FakeContext(store, [job.id]))  # type: ignore[arg-type]

    updated = await store.jobs.get(job.id)
    assert updated is not None
    assert updated.status.value == "published"
    assert "published" in pub.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_cannot_publish_incomplete_job() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _create_job(store, 1, "Engineer")

    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]
    job_id = job.id

    pub = FakeUpdate(1)
    await publish(pub, FakeContext(store, [job_id]))  # type: ignore[arg-type]

    updated = await store.jobs.get(job_id)
    assert updated is not None
    assert updated.status.value == "draft"
    assert "Cannot publish" in pub.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_owner_closes_a_published_job() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _create_job(store, 1, "Engineer")

    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]
    await set_description(FakeUpdate(1), FakeContext(store, [job.id, "d"]))  # type: ignore[arg-type]
    await set_requirements(FakeUpdate(1), FakeContext(store, [job.id, "r"]))  # type: ignore[arg-type]
    await publish(FakeUpdate(1), FakeContext(store, [job.id]))  # type: ignore[arg-type]

    await close(FakeUpdate(1), FakeContext(store, [job.id]))  # type: ignore[arg-type]

    updated = await store.jobs.get(job.id)
    assert updated is not None
    assert updated.status.value == "closed"


@pytest.mark.asyncio
async def test_owner_archives_a_closed_job() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _create_job(store, 1, "Engineer")

    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]
    await set_description(FakeUpdate(1), FakeContext(store, [job.id, "d"]))  # type: ignore[arg-type]
    await set_requirements(FakeUpdate(1), FakeContext(store, [job.id, "r"]))  # type: ignore[arg-type]
    await publish(FakeUpdate(1), FakeContext(store, [job.id]))  # type: ignore[arg-type]
    await close(FakeUpdate(1), FakeContext(store, [job.id]))  # type: ignore[arg-type]

    await archive(FakeUpdate(1), FakeContext(store, [job.id]))  # type: ignore[arg-type]

    updated = await store.jobs.get(job.id)
    assert updated is not None
    assert updated.status.value == "archived"


@pytest.mark.asyncio
async def test_cannot_archive_a_draft() -> None:
    store = make_store()
    await _create_company(store, 1, "Acme")
    await _create_job(store, 1, "Engineer")

    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]

    arc = FakeUpdate(1)
    await archive(arc, FakeContext(store, [job.id]))  # type: ignore[arg-type]

    updated = await store.jobs.get(job.id)
    assert updated is not None
    assert updated.status.value == "draft"
    assert "Cannot archive" in arc.effective_chat.messages[-1]
