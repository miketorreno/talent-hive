import asyncpg
import pytest
from domain.application import Application
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from domain.company import Company, CompanyError
from domain.identities import Role, User
from domain.job import Job, JobStatus
from domain.profile import SeekerProfile
from shared.postgres import PostgresStore


def _job(job_id: str, company_id: str, title: str, *, publish: bool = False) -> Job:
    job = Job(
        id=job_id,
        company_id=company_id,
        title=title,
        description="d",
        requirements="r",
    )
    if publish:
        job.publish()
    return job


def _cover_letter(artifact_id: str, owner_id: int, text: str) -> Artifact:
    return Artifact(
        id=artifact_id,
        type=ArtifactType.COVER_LETTER,
        owner_id=owner_id,
        origin=ArtifactOrigin.AI_GENERATED,
        text=text,
    )


@pytest.mark.asyncio
async def test_unknown_user_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.users.get(999) is None


@pytest.mark.asyncio
async def test_user_roundtrip_both_roles(pg_store: PostgresStore) -> None:
    roles = frozenset({Role.EMPLOYER, Role.JOB_SEEKER})
    await pg_store.users.save(User(telegram_id=1, roles=roles))
    loaded = await pg_store.users.get(1)
    assert loaded is not None
    assert loaded.roles == roles


@pytest.mark.asyncio
async def test_user_save_replaces_roles(pg_store: PostgresStore) -> None:
    await pg_store.users.save(User(telegram_id=1, roles=frozenset({Role.EMPLOYER})))
    await pg_store.users.save(User(telegram_id=1, roles=frozenset({Role.JOB_SEEKER})))
    loaded = await pg_store.users.get(1)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.JOB_SEEKER})


@pytest.mark.asyncio
async def test_user_empty_roles_roundtrip(pg_store: PostgresStore) -> None:
    await pg_store.users.save(User(telegram_id=2, roles=frozenset()))
    loaded = await pg_store.users.get(2)
    assert loaded is not None
    assert loaded.roles == frozenset()


@pytest.mark.asyncio
async def test_unknown_company_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.companies.get("nope") is None


@pytest.mark.asyncio
async def test_company_roundtrip(pg_store: PostgresStore) -> None:
    company = Company(id="c1", name="Acme", owner_id=1)
    company.add_recruiter(2)
    await pg_store.companies.save(company)
    loaded = await pg_store.companies.get("c1")
    assert loaded is not None
    assert loaded.name == "Acme"
    assert loaded.owner_id == 1
    assert loaded.recruiter_ids == {2}


@pytest.mark.asyncio
async def test_company_find_by_owner(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    company = await pg_store.companies.find_by_owner(1)
    assert company is not None
    assert company.id == "c1"


@pytest.mark.asyncio
async def test_company_find_by_member_recruiter(pg_store: PostgresStore) -> None:
    company = Company(id="c1", name="Acme", owner_id=1)
    company.add_recruiter(2)
    await pg_store.companies.save(company)
    found = await pg_store.companies.find_by_member(2)
    assert found is not None
    assert found.id == "c1"


@pytest.mark.asyncio
async def test_owner_cannot_own_two_companies(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    with pytest.raises(CompanyError, match="one company"):
        await pg_store.companies.save(Company(id="c2", name="Globex", owner_id=1))


@pytest.mark.asyncio
async def test_delete_company(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.companies.delete("c1")
    assert await pg_store.companies.get("c1") is None
    assert await pg_store.companies.find_by_owner(1) is None


@pytest.mark.asyncio
async def test_unknown_job_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.jobs.get("nope") is None


@pytest.mark.asyncio
async def test_job_roundtrip(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    job = _job("j1", "c1", "Engineer", publish=True)
    await pg_store.jobs.save(job)
    loaded = await pg_store.jobs.get("j1")
    assert loaded is not None
    assert loaded.title == "Engineer"
    assert loaded.status == JobStatus.PUBLISHED
    assert loaded.requirements == "r"


@pytest.mark.asyncio
async def test_list_jobs_by_company(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.companies.save(Company(id="c2", name="Globex", owner_id=2))
    await pg_store.jobs.save(_job("j1", "c1", "Engineer"))
    await pg_store.jobs.save(_job("j2", "c1", "Designer"))
    await pg_store.jobs.save(_job("j3", "c2", "Ops"))
    company_jobs = await pg_store.jobs.list_by_company("c1")
    assert {j.id for j in company_jobs} == {"j1", "j2"}


@pytest.mark.asyncio
async def test_list_published(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.jobs.save(_job("j1", "c1", "Draft"))
    await pg_store.jobs.save(_job("j2", "c1", "Live", publish=True))
    titles = {j.title for j in await pg_store.jobs.list_published()}
    assert titles == {"Live"}


@pytest.mark.asyncio
async def test_unknown_profile_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.profiles.get(999) is None


@pytest.mark.asyncio
async def test_profile_roundtrip(pg_store: PostgresStore) -> None:
    profile = SeekerProfile(
        seeker_id=1, skills=["python", "sql"], experience=["x"], background="hi"
    )
    await pg_store.profiles.save(profile)
    loaded = await pg_store.profiles.get(1)
    assert loaded is not None
    assert loaded.skills == ["python", "sql"]
    assert loaded.experience == ["x"]
    assert loaded.background == "hi"


@pytest.mark.asyncio
async def test_profile_save_updates(pg_store: PostgresStore) -> None:
    await pg_store.profiles.save(SeekerProfile(seeker_id=1, skills=["python"], background="a"))
    updated = SeekerProfile(seeker_id=1, skills=["python", "go"], background="b")
    await pg_store.profiles.save(updated)
    loaded = await pg_store.profiles.get(1)
    assert loaded is not None
    assert loaded.skills == ["python", "go"]


@pytest.mark.asyncio
async def test_unknown_application_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.applications.get("nope") is None


@pytest.mark.asyncio
async def test_application_roundtrip(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.jobs.save(_job("j1", "c1", "Engineer"))
    application = Application(id="a1", job_id="j1", seeker_id=9, cover_letter="cover")
    await pg_store.applications.save(application)
    loaded = await pg_store.applications.get("a1")
    assert loaded is not None
    assert loaded.job_id == "j1"
    assert loaded.seeker_id == 9
    assert loaded.cover_letter == "cover"


@pytest.mark.asyncio
async def test_application_list_by_job_and_seeker(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.jobs.save(_job("j1", "c1", "Engineer"))
    await pg_store.applications.save(Application(id="a1", job_id="j1", seeker_id=1))
    await pg_store.applications.save(Application(id="a2", job_id="j1", seeker_id=2))
    assert {a.id for a in await pg_store.applications.list_by_job("j1")} == {"a1", "a2"}
    assert {a.id for a in await pg_store.applications.list_by_seeker(1)} == {"a1"}


@pytest.mark.asyncio
async def test_application_dedup_via_unique_constraint(pg_store: PostgresStore) -> None:
    await pg_store.companies.save(Company(id="c1", name="Acme", owner_id=1))
    await pg_store.jobs.save(_job("j1", "c1", "Engineer"))
    await pg_store.applications.save(Application(id="a1", job_id="j1", seeker_id=1))
    with pytest.raises(asyncpg.UniqueViolationError):
        await pg_store.applications.save(Application(id="a2", job_id="j1", seeker_id=1))


@pytest.mark.asyncio
async def test_unknown_artifact_is_none(pg_store: PostgresStore) -> None:
    assert await pg_store.artifacts.get("nope") is None


@pytest.mark.asyncio
async def test_artifact_roundtrip(pg_store: PostgresStore) -> None:
    artifact = Artifact(
        id="ar1",
        type=ArtifactType.COVER_LETTER,
        owner_id=1,
        origin=ArtifactOrigin.AI_GENERATED,
        text="hello",
    )
    await pg_store.artifacts.save(artifact)
    loaded = await pg_store.artifacts.get("ar1")
    assert loaded is not None
    assert loaded.type == ArtifactType.COVER_LETTER
    assert loaded.origin == ArtifactOrigin.AI_GENERATED
    assert loaded.text == "hello"


@pytest.mark.asyncio
async def test_artifact_list_by_owner_and_type(pg_store: PostgresStore) -> None:
    await pg_store.artifacts.save(_cover_letter("ar1", 1, "a"))
    await pg_store.artifacts.save(_cover_letter("ar3", 2, "c"))
    resume = Artifact(
        id="ar2",
        type=ArtifactType.RESUME,
        owner_id=1,
        origin=ArtifactOrigin.AI_GENERATED,
        text="b",
    )
    await pg_store.artifacts.save(resume)
    all_for_owner = await pg_store.artifacts.list_by_owner(1)
    assert {a.id for a in all_for_owner} == {"ar1", "ar2"}
    resumes = await pg_store.artifacts.list_by_owner(1, type=ArtifactType.RESUME)
    assert {a.id for a in resumes} == {"ar2"}


@pytest.mark.asyncio
async def test_one_resume_per_user_constraint(pg_store: PostgresStore) -> None:
    await pg_store.artifacts.save(
        Artifact(
            id="ar1",
            type=ArtifactType.RESUME,
            owner_id=1,
            origin=ArtifactOrigin.AI_GENERATED,
            text="r1",
        )
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await pg_store.artifacts.save(
            Artifact(
                id="ar2",
                type=ArtifactType.RESUME,
                owner_id=1,
                origin=ArtifactOrigin.AI_GENERATED,
                text="r2",
            )
        )


@pytest.mark.asyncio
async def test_multiple_cover_letters_per_user_allowed(pg_store: PostgresStore) -> None:
    await pg_store.artifacts.save(_cover_letter("ar1", 1, "c1"))
    await pg_store.artifacts.save(_cover_letter("ar2", 1, "c2"))
    letters = await pg_store.artifacts.list_by_owner(1, type=ArtifactType.COVER_LETTER)
    assert {a.id for a in letters} == {"ar1", "ar2"}
