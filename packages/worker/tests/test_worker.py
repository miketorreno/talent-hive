import builtins

import pytest
import worker.main as worker_main
from ai.providers import Provider, ProviderError
from ai.router import ProviderRouter
from domain.artifact import ArtifactOrigin, ArtifactType
from domain.company import Company
from domain.job import Job
from domain.profile import SeekerProfile
from shared.config import Settings
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
    """In-memory stand-in for the redis commands the worker repo calls."""

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


class FakeProvider(Provider):
    id = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return "A polished generated artifact."


@pytest.fixture
def store() -> Store:
    redis = FakeRedis()
    return Store(
        users=RedisUserRepository(redis),  # type: ignore[arg-type]
        companies=RedisCompanyRepository(redis),  # type: ignore[arg-type]
        jobs=RedisJobRepository(redis),  # type: ignore[arg-type]
        profiles=RedisSeekerProfileRepository(redis),  # type: ignore[arg-type]
        applications=RedisApplicationRepository(redis),  # type: ignore[arg-type]
        artifacts=RedisArtifactRepository(redis),  # type: ignore[arg-type]
    )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


def _patch_environment(monkeypatch, store: Store, provider: FakeProvider) -> None:
    def fake_build_store(url: str) -> Store:
        return store

    def fake_router(settings: Settings, http_client=None):
        return ProviderRouter(settings, [provider])

    monkeypatch.setattr(worker_main, "build_store", fake_build_store)
    monkeypatch.setattr(worker_main, "build_router", fake_router)


@pytest.mark.asyncio
async def test_cover_letter_generation_persists_artifact(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    profile = SeekerProfile(seeker_id=7)
    profile.add_skill("Python")
    profile.set_background("5 years backend")
    await store.profiles.save(profile)
    await store.jobs.save(
        Job(id="j1", company_id="c1", title="Engineer", description="Build", requirements="Python")
    )
    _patch_environment(monkeypatch, store, provider)

    artifact_id = await worker_main.generate_artifact({}, "cover_letter", 7, job_id="j1")

    artifact = await store.artifacts.get(artifact_id)
    assert artifact is not None
    assert artifact.origin == ArtifactOrigin.AI_GENERATED
    assert artifact.type == ArtifactType.COVER_LETTER
    assert artifact.owner_id == 7
    assert artifact.text == "A polished generated artifact."
    system, user = provider.calls[0]
    assert "Engineer" in user
    assert "5 years backend" in user


@pytest.mark.asyncio
async def test_cover_letter_includes_company_name(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    profile = SeekerProfile(seeker_id=7)
    profile.add_skill("Python")
    profile.set_background("5 years backend")
    await store.profiles.save(profile)
    await store.companies.save(Company(id="c1", name="Acme Corp"))
    await store.jobs.save(
        Job(
            id="j1",
            company_id="c1",
            title="Engineer",
            description="Build",
            requirements="Python",
        )
    )
    _patch_environment(monkeypatch, store, provider)

    await worker_main.generate_artifact({}, "cover_letter", 7, job_id="j1")

    _, user = provider.calls[0]
    assert "Acme Corp" in user


@pytest.mark.asyncio
async def test_resume_generation_persists_artifact(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    profile = SeekerProfile(seeker_id=7)
    profile.add_skill("Python")
    profile.set_background("5 years backend")
    await store.profiles.save(profile)
    _patch_environment(monkeypatch, store, provider)

    artifact_id = await worker_main.generate_artifact({}, "resume", 7)

    artifact = await store.artifacts.get(artifact_id)
    assert artifact is not None
    assert artifact.type == ArtifactType.RESUME
    assert artifact.text == "A polished generated artifact."


@pytest.mark.asyncio
async def test_job_description_generation_requires_job(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    _patch_environment(monkeypatch, store, provider)
    with pytest.raises(ProviderError):
        await worker_main.generate_artifact({}, "job_description", 7)


@pytest.mark.asyncio
async def test_job_description_generation_applies_refinement_goals(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    await store.jobs.save(
        Job(id="j1", company_id="c1", title="Engineer", description="Build", requirements="Python")
    )
    _patch_environment(monkeypatch, store, provider)

    await worker_main.generate_artifact(
        {}, "job_description", 7, job_id="j1", goals=["clarity", "shorter"]
    )

    _, user = provider.calls[0]
    assert "clearer" in user
    assert "shorter" in user


@pytest.mark.asyncio
async def test_job_description_generation_without_goals_omits_them(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    await store.jobs.save(
        Job(id="j1", company_id="c1", title="Engineer", description="Build", requirements="Python")
    )
    _patch_environment(monkeypatch, store, provider)

    await worker_main.generate_artifact({}, "job_description", 7, job_id="j1")

    _, user = provider.calls[0]
    assert "REFINEMENT" not in user


@pytest.mark.asyncio
async def test_resume_generation_requires_profile(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    _patch_environment(monkeypatch, store, provider)
    with pytest.raises(ProviderError):
        await worker_main.generate_artifact({}, "resume", 7)


@pytest.mark.asyncio
async def test_cover_letter_generation_requires_profile(
    monkeypatch, store: Store, provider: FakeProvider
) -> None:
    await store.jobs.save(
        Job(id="j1", company_id="c1", title="Engineer", description="Build", requirements="Python")
    )
    _patch_environment(monkeypatch, store, provider)
    with pytest.raises(ProviderError):
        await worker_main.generate_artifact({}, "cover_letter", 7, job_id="j1")


def test_worker_settings_exposes_generation_job() -> None:
    assert worker_main.WorkerSettings.functions == [worker_main.generate_artifact]
