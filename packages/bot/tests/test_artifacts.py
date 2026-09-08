import pytest
from _bot_helpers import (
    FakeArq,
    FakeContext,
    FakeDocument,
    FakeUpdate,
    make_store,
    register_employer,
    register_seeker,
)
from bot.artifacts import (
    artifact as artifact_cmd,
)
from bot.artifacts import (
    artifacts,
    coverletter,
    refinejd,
    resume,
    upload,
    write,
)
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from domain.company import Company
from domain.job import Job
from domain.profile import SeekerProfile

_JOB = Job(
    id="j1",
    company_id="c1",
    title="Engineer",
    description="d",
    requirements="r",
)


async def _published_job(store, job_id: str = "j1") -> None:
    job = Job(
        id=job_id,
        company_id="c1",
        title="Engineer",
        description="d",
        requirements="r",
    )
    job.publish()
    await store.jobs.save(job)


def _written_artifact(*, id: str, owner_id: int) -> Artifact:
    return Artifact(
        id=id,
        type=ArtifactType.RESUME,
        owner_id=owner_id,
        origin=ArtifactOrigin.USER_WRITTEN,
        text="t",
    )


def _cover_letter_saved(*, owner_id: int) -> Artifact:
    return Artifact(
        id="a1",
        type=ArtifactType.COVER_LETTER,
        owner_id=owner_id,
        origin=ArtifactOrigin.AI_GENERATED,
        text="hello world",
    )


def _resume_uploaded(*, id: str, owner_id: int, key: str) -> Artifact:
    return Artifact(
        id=id,
        type=ArtifactType.RESUME,
        owner_id=owner_id,
        origin=ArtifactOrigin.USER_UPLOADED,
        storage_key=key,
    )


@pytest.mark.asyncio
async def test_coverletter_requires_seeker_role() -> None:
    store = make_store()
    update = FakeUpdate(1)
    await coverletter(update, FakeContext(store, ["j1"]))  # type: ignore[arg-type]
    assert "Job Seeker role" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_coverletter_queues_generation() -> None:
    store = make_store()
    await register_seeker(store, 1)
    profile = SeekerProfile(seeker_id=1)
    profile.set_background("backend")
    await store.profiles.save(profile)
    await _published_job(store)
    arq = FakeArq()
    update = FakeUpdate(1)

    await coverletter(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    assert arq.jobs == [
        ("generate_artifact", ("cover_letter", 1), {"job_id": "j1", "goals": None})
    ]
    assert "queued" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_coverletter_rejects_unpublished_job() -> None:
    store = make_store()
    await register_seeker(store, 1)
    profile = SeekerProfile(seeker_id=1)
    profile.set_background("backend")
    await store.profiles.save(profile)
    await store.jobs.save(_JOB)
    arq = FakeArq()
    update = FakeUpdate(1)

    await coverletter(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    assert arq.jobs == []
    assert "not open" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_coverletter_requires_profile() -> None:
    store = make_store()
    await register_seeker(store, 1)
    await _published_job(store)
    arq = FakeArq()
    update = FakeUpdate(1)

    await coverletter(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    assert arq.jobs == []
    assert "Seeker Profile" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_resume_queues_generation() -> None:
    store = make_store()
    await register_seeker(store, 1)
    profile = SeekerProfile(seeker_id=1)
    profile.set_background("backend")
    await store.profiles.save(profile)
    arq = FakeArq()
    update = FakeUpdate(1)

    await resume(update, FakeContext(store, arq=arq))  # type: ignore[arg-type]

    expected = (
        "generate_artifact",
        ("resume", 1),
        {"job_id": None, "goals": None},
    )
    assert arq.jobs == [expected]
    assert "queued" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_resume_queues_generation_with_job() -> None:
    store = make_store()
    await register_seeker(store, 1)
    profile = SeekerProfile(seeker_id=1)
    profile.set_background("backend")
    await store.profiles.save(profile)
    await _published_job(store)
    arq = FakeArq()
    update = FakeUpdate(1)

    await resume(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    expected = ("generate_artifact", ("resume", 1), {"job_id": "j1", "goals": None})
    assert arq.jobs == [expected]
    assert "queued" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_resume_rejects_unpublished_job() -> None:
    store = make_store()
    await register_seeker(store, 1)
    profile = SeekerProfile(seeker_id=1)
    profile.set_background("backend")
    await store.profiles.save(profile)
    await store.jobs.save(_JOB)
    arq = FakeArq()
    update = FakeUpdate(1)

    await resume(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    assert arq.jobs == []
    assert "not open" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_resume_requires_profile() -> None:
    store = make_store()
    await register_seeker(store, 1)
    arq = FakeArq()
    update = FakeUpdate(1)

    await resume(update, FakeContext(store, arq=arq))  # type: ignore[arg-type]

    assert arq.jobs == []
    assert "Seeker Profile" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_refinejd_requires_employer() -> None:
    store = make_store()
    update = FakeUpdate(1)
    ctx = FakeContext(store, ["j1"])
    await refinejd(update, ctx)  # type: ignore[arg-type]
    assert "Employer role" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_refinejd_queues_generation_for_company_job() -> None:
    store = make_store()
    await register_employer(store, 1)
    company = Company(id="c1", name="Acme")
    company.set_owner(1)
    await store.companies.save(company)
    await store.jobs.save(_JOB)
    arq = FakeArq()
    update = FakeUpdate(1)

    await refinejd(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    expected = (
        "generate_artifact",
        ("job_description", 1),
        {"job_id": "j1", "goals": None},
    )
    assert arq.jobs == [expected]
    assert "queued" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_refinejd_passes_refinement_goals() -> None:
    store = make_store()
    await register_employer(store, 1)
    company = Company(id="c1", name="Acme")
    company.set_owner(1)
    await store.companies.save(company)
    await store.jobs.save(_JOB)
    arq = FakeArq()
    update = FakeUpdate(1)

    await refinejd(
        update, FakeContext(store, ["j1", "clarity", "skills", "shorter"], arq=arq)  # type: ignore[arg-type]
    )

    expected = (
        "generate_artifact",
        ("job_description", 1),
        {"job_id": "j1", "goals": ["clarity", "skills", "shorter"]},
    )
    assert arq.jobs == [expected]
    assert "goals" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_refinejd_rejects_other_companys_job() -> None:
    store = make_store()
    await register_employer(store, 1)
    own = Company(id="c1", name="Acme")
    own.set_owner(1)
    await store.companies.save(own)
    other = Company(id="c2", name="Other")
    other.set_owner(2)
    await store.companies.save(other)
    await store.jobs.save(
        Job(
            id="j1",
            company_id="c2",
            title="Engineer",
            description="d",
            requirements="r",
        )
    )
    arq = FakeArq()
    update = FakeUpdate(1)

    await refinejd(
        update, FakeContext(store, ["j1"], arq=arq)  # type: ignore[arg-type]
    )

    assert arq.jobs == []
    assert "in your company" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_artifacts_lists_owned_artifacts() -> None:
    store = make_store()
    await store.artifacts.save(_written_artifact(id="a1", owner_id=1))
    await store.artifacts.save(_written_artifact(id="a2", owner_id=2))
    update = FakeUpdate(1)

    await artifacts(update, FakeContext(store))  # type: ignore[arg-type]

    assert "a1" in update.effective_chat.messages[-1]
    assert "a2" not in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_artifact_redelivers_text() -> None:
    store = make_store()
    await store.artifacts.save(_cover_letter_saved(owner_id=1))
    update = FakeUpdate(1)

    await artifact_cmd(update, FakeContext(store, ["a1"]))  # type: ignore[arg-type]

    assert "hello world" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_artifact_hides_other_owners_artifact() -> None:
    store = make_store()
    await store.artifacts.save(
        Artifact(
            id="a1",
            type=ArtifactType.RESUME,
            owner_id=2,
            origin=ArtifactOrigin.USER_WRITTEN,
            text="secret",
        )
    )
    update = FakeUpdate(1)

    await artifact_cmd(update, FakeContext(store, ["a1"]))  # type: ignore[arg-type]

    assert "not found" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_artifact_redelivers_uploaded_document() -> None:
    store = make_store()
    await store.artifacts.save(
        _resume_uploaded(id="a1", owner_id=1, key="FILE1")
    )
    update = FakeUpdate(1)

    await artifact_cmd(update, FakeContext(store, ["a1"]))  # type: ignore[arg-type]

    assert update.effective_chat.documents == ["FILE1"]


@pytest.mark.asyncio
async def test_write_saves_user_written_artifact() -> None:
    store = make_store()
    update = FakeUpdate(1)
    args = ["resume", "my", "resume", "text"]

    await write(update, FakeContext(store, args))  # type: ignore[arg-type]

    owned = await store.artifacts.list_by_owner(1)
    assert len(owned) == 1
    assert owned[0].origin == ArtifactOrigin.USER_WRITTEN
    assert owned[0].text == "my resume text"
    assert "saved" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_upload_saves_uploaded_artifact() -> None:
    store = make_store()
    update = FakeUpdate(1, document=FakeDocument("FILE42"))

    await upload(update, FakeContext(store, ["resume"]))  # type: ignore[arg-type]

    owned = await store.artifacts.list_by_owner(1)
    assert len(owned) == 1
    assert owned[0].origin == ArtifactOrigin.USER_UPLOADED
    assert owned[0].storage_key == "FILE42"
    assert "uploaded" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_upload_needs_document() -> None:
    store = make_store()
    update = FakeUpdate(1)

    await upload(update, FakeContext(store, ["resume"]))  # type: ignore[arg-type]

    assert "Attach a document" in update.effective_chat.messages[-1]
