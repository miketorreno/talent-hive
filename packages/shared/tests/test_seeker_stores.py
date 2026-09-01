import pytest
from _shared_helpers import FakeRedis
from domain.application import Application
from domain.job import Job
from domain.profile import SeekerProfile
from shared.store import (
    ApplicationRepository,
    JobRepository,
    RedisApplicationRepository,
    RedisJobRepository,
    RedisSeekerProfileRepository,
    SeekerProfileRepository,
)


@pytest.fixture
def profile_repo() -> SeekerProfileRepository:
    return RedisSeekerProfileRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.fixture
def application_repo() -> ApplicationRepository:
    return RedisApplicationRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.fixture
def job_repo() -> JobRepository:
    return RedisJobRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_unknown_profile_is_none(
    profile_repo: SeekerProfileRepository,
) -> None:
    assert await profile_repo.get(999) is None


@pytest.mark.asyncio
async def test_save_and_get_profile_roundtrip(
    profile_repo: SeekerProfileRepository,
) -> None:
    profile = SeekerProfile(seeker_id=7)
    profile.add_skill("Python")
    profile.add_experience("Built a bot")
    profile.set_background("5 years backend")
    await profile_repo.save(profile)
    loaded = await profile_repo.get(7)
    assert loaded is not None
    assert loaded.skills == ["Python"]
    assert loaded.experience == ["Built a bot"]
    assert loaded.background == "5 years backend"
    assert loaded.updated_at == profile.updated_at


@pytest.mark.asyncio
async def test_unknown_application_is_none(
    application_repo: ApplicationRepository,
) -> None:
    assert await application_repo.get("nope") is None


@pytest.mark.asyncio
async def test_save_and_get_application_roundtrip(
    application_repo: ApplicationRepository,
) -> None:
    application = Application(id="a1", job_id="j1", seeker_id=7)
    application.start_review()
    await application_repo.save(application)
    loaded = await application_repo.get("a1")
    assert loaded is not None
    assert loaded.job_id == "j1"
    assert loaded.seeker_id == 7
    assert loaded.status.value == "under_review"
    assert loaded.created_at == application.created_at


@pytest.mark.asyncio
async def test_list_applications_by_job(
    application_repo: ApplicationRepository,
) -> None:
    await application_repo.save(Application(id="a1", job_id="j1", seeker_id=7))
    await application_repo.save(Application(id="a2", job_id="j1", seeker_id=8))
    await application_repo.save(Application(id="a3", job_id="j2", seeker_id=9))
    apps = await application_repo.list_by_job("j1")
    assert {a.id for a in apps} == {"a1", "a2"}


@pytest.mark.asyncio
async def test_list_applications_by_seeker(
    application_repo: ApplicationRepository,
) -> None:
    await application_repo.save(Application(id="a1", job_id="j1", seeker_id=7))
    await application_repo.save(Application(id="a2", job_id="j2", seeker_id=7))
    await application_repo.save(Application(id="a3", job_id="j3", seeker_id=8))
    apps = await application_repo.list_by_seeker(7)
    assert {a.id for a in apps} == {"a1", "a2"}


@pytest.mark.asyncio
async def test_list_published_excludes_non_published(
    job_repo: JobRepository,
) -> None:
    published = Job(
        id="j1", company_id="c1", title="A", description="d", requirements="r"
    )
    published.publish()
    await job_repo.save(published)
    await job_repo.save(
        Job(id="j2", company_id="c1", title="B", description="d", requirements="r")
    )
    result = await job_repo.list_published()
    assert {job.id for job in result} == {"j1"}


@pytest.mark.asyncio
async def test_list_published_updates_when_job_leaves_published(
    job_repo: JobRepository,
) -> None:
    published = Job(
        id="j1", company_id="c1", title="A", description="d", requirements="r"
    )
    published.publish()
    await job_repo.save(published)
    published.close()
    await job_repo.save(published)
    assert await job_repo.list_published() == []


@pytest.mark.asyncio
async def test_delete_job_removes_from_published(
    job_repo: JobRepository,
) -> None:
    published = Job(
        id="j1", company_id="c1", title="A", description="d", requirements="r"
    )
    published.publish()
    await job_repo.save(published)
    await job_repo.delete("j1")
    assert await job_repo.list_published() == []
