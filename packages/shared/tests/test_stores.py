import builtins

import pytest
from domain.company import Company, CompanyError
from domain.job import Job, JobStatus
from shared.store import (
    CompanyRepository,
    JobRepository,
    RedisCompanyRepository,
    RedisJobRepository,
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


@pytest.fixture
def company_repo() -> CompanyRepository:
    return RedisCompanyRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.fixture
def job_repo() -> JobRepository:
    return RedisJobRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_unknown_company_is_none(company_repo: CompanyRepository) -> None:
    assert await company_repo.get("nope") is None


@pytest.mark.asyncio
async def test_save_and_get_company_roundtrip(company_repo: CompanyRepository) -> None:
    company = Company(id="c1", name="Acme", owner_id=7)
    company.add_recruiter(9)
    await company_repo.save(company)
    loaded = await company_repo.get("c1")
    assert loaded is not None
    assert loaded.name == "Acme"
    assert loaded.owner_id == 7
    assert loaded.recruiter_ids == {9}


@pytest.mark.asyncio
async def test_find_by_owner(company_repo: CompanyRepository) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    company = await company_repo.find_by_owner(7)
    assert company is not None
    assert company.id == "c1"


@pytest.mark.asyncio
async def test_find_by_owner_unknown_owner_is_none(company_repo: CompanyRepository) -> None:
    assert await company_repo.find_by_owner(999) is None


@pytest.mark.asyncio
async def test_find_by_member_finds_owner(company_repo: CompanyRepository) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    company = await company_repo.find_by_member(7)
    assert company is not None
    assert company.id == "c1"


@pytest.mark.asyncio
async def test_find_by_member_finds_recruiter(company_repo: CompanyRepository) -> None:
    company = Company(id="c1", name="Acme", owner_id=7)
    company.add_recruiter(9)
    await company_repo.save(company)
    found = await company_repo.find_by_member(9)
    assert found is not None
    assert found.id == "c1"


@pytest.mark.asyncio
async def test_find_by_member_unknown_is_none(company_repo: CompanyRepository) -> None:
    assert await company_repo.find_by_member(999) is None


@pytest.mark.asyncio
async def test_add_recruiter_updates_member_index(company_repo: CompanyRepository) -> None:
    company = Company(id="c1", name="Acme", owner_id=7)
    await company_repo.save(company)
    company.add_recruiter(9)
    await company_repo.save(company)
    assert (await company_repo.find_by_member(9)) is not None


@pytest.mark.asyncio
async def test_delete_company_clears_member_index(company_repo: CompanyRepository) -> None:
    company = Company(id="c1", name="Acme", owner_id=7)
    company.add_recruiter(9)
    await company_repo.save(company)
    await company_repo.delete("c1")
    assert await company_repo.find_by_member(7) is None
    assert await company_repo.find_by_member(9) is None


@pytest.mark.asyncio
async def test_company_without_owner_has_no_owner_index(company_repo: CompanyRepository) -> None:
    await company_repo.save(Company(id="c1", name="Acme"))
    assert await company_repo.find_by_owner(7) is None


@pytest.mark.asyncio
async def test_delete_company(company_repo: CompanyRepository) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    await company_repo.delete("c1")
    assert await company_repo.get("c1") is None
    assert await company_repo.find_by_owner(7) is None


@pytest.mark.asyncio
async def test_save_company_under_existing_owner_is_idempotent(
    company_repo: CompanyRepository,
) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    updated = Company(id="c1", name="Acme 2", owner_id=7)
    await company_repo.save(updated)
    loaded = await company_repo.get("c1")
    assert loaded is not None
    assert loaded.name == "Acme 2"


@pytest.mark.asyncio
async def test_owner_cannot_own_two_companies(
    company_repo: CompanyRepository,
) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    with pytest.raises(CompanyError, match="one company"):
        await company_repo.save(Company(id="c2", name="Globex", owner_id=7))


@pytest.mark.asyncio
async def test_save_does_not_affect_other_company_on_rejected_owner(
    company_repo: CompanyRepository,
) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    with pytest.raises(CompanyError):
        await company_repo.save(Company(id="c2", name="Globex", owner_id=7))
    assert await company_repo.get("c2") is None


@pytest.mark.asyncio
async def test_distinct_owners_may_each_own_a_company(
    company_repo: CompanyRepository,
) -> None:
    await company_repo.save(Company(id="c1", name="Acme", owner_id=7))
    await company_repo.save(Company(id="c2", name="Globex", owner_id=8))
    assert (await company_repo.find_by_owner(7)) is not None
    assert (await company_repo.find_by_owner(8)) is not None


@pytest.mark.asyncio
async def test_save_unowned_company_is_allowed(
    company_repo: CompanyRepository,
) -> None:
    await company_repo.save(Company(id="c1", name="Acme"))
    assert await company_repo.get("c1") is not None


@pytest.mark.asyncio
async def test_unknown_job_is_none(job_repo: JobRepository) -> None:
    assert await job_repo.get("nope") is None


@pytest.mark.asyncio
async def test_save_and_get_job_roundtrip(job_repo: JobRepository) -> None:
    job = Job(
        id="j1",
        company_id="c1",
        title="Engineer",
        description="Build things",
        requirements="Python",
        created_by=7,
    )
    job.publish()
    await job_repo.save(job)
    loaded = await job_repo.get("j1")
    assert loaded is not None
    assert loaded.title == "Engineer"
    assert loaded.status == JobStatus.PUBLISHED
    assert loaded.created_by == 7
    assert loaded.created_at == job.created_at


@pytest.mark.asyncio
async def test_list_jobs_by_company(job_repo: JobRepository) -> None:
    await job_repo.save(
        Job(id="j1", company_id="c1", title="Engineer", description="d", requirements="r")
    )
    await job_repo.save(
        Job(id="j2", company_id="c1", title="Designer", description="d", requirements="r")
    )
    await job_repo.save(
        Job(id="j3", company_id="c2", title="Ops", description="d", requirements="r")
    )
    jobs = await job_repo.list_by_company("c1")
    assert {j.id for j in jobs} == {"j1", "j2"}


@pytest.mark.asyncio
async def test_delete_job(job_repo: JobRepository) -> None:
    await job_repo.save(Job(id="j1", company_id="c1", title="Engineer", description="d"))
    await job_repo.delete("j1")
    assert await job_repo.get("j1") is None
    assert await job_repo.list_by_company("c1") == []


def _published_job(job_id: str, title: str, description: str = "d") -> Job:
    job = Job(id=job_id, company_id="c1", title=title, description=description, requirements="r")
    job.publish()
    return job


@pytest.mark.asyncio
async def test_search_published_matches_title(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    await job_repo.save(_published_job("j2", "Frontend Designer"))
    matches = await job_repo.search_published("backend")
    assert {j.id for j in matches} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_matches_description(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Engineer", description="Build Python services"))
    matches = await job_repo.search_published("python")
    assert {j.id for j in matches} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_matches_requirements(job_repo: JobRepository) -> None:
    job = Job(id="j1", company_id="c1", title="Engineer", description="d", requirements="SQL, Go")
    job.publish()
    await job_repo.save(job)
    matches = await job_repo.search_published("sql")
    assert {j.id for j in matches} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_is_case_insensitive(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    assert {j.id for j in await job_repo.search_published("BACKEND")} == {"j1"}
    assert {j.id for j in await job_repo.search_published("BackEnd")} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_requires_all_terms(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    await job_repo.save(_published_job("j2", "Backend Designer"))
    matches = await job_repo.search_published("backend engineer")
    assert {j.id for j in matches} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_ignores_unpublished_jobs(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    await job_repo.save(Job(id="j2", company_id="c1", title="Backend Ghost", description="d"))
    matches = await job_repo.search_published("backend")
    assert {j.id for j in matches} == {"j1"}


@pytest.mark.asyncio
async def test_search_published_no_match(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    assert await job_repo.search_published("rust") == []


@pytest.mark.asyncio
async def test_search_published_empty_query(job_repo: JobRepository) -> None:
    await job_repo.save(_published_job("j1", "Backend Engineer"))
    assert await job_repo.search_published("   ") == []
