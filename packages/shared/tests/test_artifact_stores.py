import pytest
from _shared_helpers import FakeRedis
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from shared.store import ArtifactRepository, RedisArtifactRepository


def _user_written(id: str, owner_id: int) -> Artifact:
    return Artifact(
        id=id,
        type=ArtifactType.RESUME,
        owner_id=owner_id,
        origin=ArtifactOrigin.USER_WRITTEN,
        text="t",
    )


@pytest.fixture
def artifact_repo() -> ArtifactRepository:
    return RedisArtifactRepository(FakeRedis())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_unknown_artifact_is_none(
    artifact_repo: ArtifactRepository,
) -> None:
    assert await artifact_repo.get("nope") is None


@pytest.mark.asyncio
async def test_save_and_get_ai_generated_roundtrip(
    artifact_repo: ArtifactRepository,
) -> None:
    artifact = Artifact(
        id="a1",
        type=ArtifactType.COVER_LETTER,
        owner_id=7,
        origin=ArtifactOrigin.AI_GENERATED,
        text="Dear Hiring Team...",
    )
    await artifact_repo.save(artifact)
    loaded = await artifact_repo.get("a1")
    assert loaded is not None
    assert loaded.type == ArtifactType.COVER_LETTER
    assert loaded.owner_id == 7
    assert loaded.origin == ArtifactOrigin.AI_GENERATED
    assert loaded.text == "Dear Hiring Team..."
    assert loaded.created_at == artifact.created_at


@pytest.mark.asyncio
async def test_save_and_get_uploaded_roundtrip(
    artifact_repo: ArtifactRepository,
) -> None:
    artifact = Artifact(
        id="a2",
        type=ArtifactType.RESUME,
        owner_id=8,
        origin=ArtifactOrigin.USER_UPLOADED,
        storage_key="s3://bucket/resume.pdf",
    )
    await artifact_repo.save(artifact)
    loaded = await artifact_repo.get("a2")
    assert loaded is not None
    assert loaded.origin == ArtifactOrigin.USER_UPLOADED
    assert loaded.storage_key == "s3://bucket/resume.pdf"


@pytest.mark.asyncio
async def test_list_by_owner(artifact_repo: ArtifactRepository) -> None:
    await artifact_repo.save(
        _user_written(id="a1", owner_id=7)
    )
    await artifact_repo.save(
        Artifact(
            id="a2",
            type=ArtifactType.COVER_LETTER,
            owner_id=7,
            origin=ArtifactOrigin.AI_GENERATED,
            text="t",
        )
    )
    await artifact_repo.save(_user_written(id="a3", owner_id=8))
    owned = await artifact_repo.list_by_owner(7)
    assert {a.id for a in owned} == {"a1", "a2"}


@pytest.mark.asyncio
async def test_list_by_owner_and_type(artifact_repo: ArtifactRepository) -> None:
    await artifact_repo.save(_user_written(id="a1", owner_id=7))
    await artifact_repo.save(
        Artifact(
            id="a2",
            type=ArtifactType.COVER_LETTER,
            owner_id=7,
            origin=ArtifactOrigin.AI_GENERATED,
            text="t",
        )
    )
    resumes = await artifact_repo.list_by_owner(7, type=ArtifactType.RESUME)
    assert {a.id for a in resumes} == {"a1"}
