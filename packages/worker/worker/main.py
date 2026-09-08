"""arq worker: consumes AI generation jobs from the Redis queue."""

from __future__ import annotations

from uuid import uuid4

from ai.factory import build_router
from ai.prompts import ArtifactContext
from ai.providers import ProviderError
from arq.connections import RedisSettings
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from domain.job import Job
from domain.profile import SeekerProfile
from domain.refinement import parse_refinement_goals
from httpx import AsyncClient
from shared.config import get_settings
from shared.store import build_store


async def _build_context(
    artifact_type: ArtifactType,
    profile: SeekerProfile | None,
    job: Job | None,
    company_name: str = "",
    goals_tokens: list[str] | None = None,
) -> ArtifactContext:
    if artifact_type in (ArtifactType.COVER_LETTER, ArtifactType.RESUME):
        if not profile:
            raise ProviderError(
                f"a seeker profile is required to generate a "
                f"{artifact_type.value.replace('_', ' ')}"
            )
        return ArtifactContext(
            job_title=job.title if job else "",
            company_name=company_name,
            description=job.description if job else "",
            requirements=job.requirements if job else "",
            background=profile.background if profile else "",
            skills=", ".join(profile.skills) if profile else "",
            experience="\n".join(profile.experience) if profile else "",
        )
    if artifact_type is ArtifactType.JOB_DESCRIPTION:
        if job is None:
            raise ProviderError(
                "a job is required to generate a job description"
            )
        return ArtifactContext(
            job_title=job.title,
            description=job.description,
            requirements=job.requirements,
            refinement_goals=parse_refinement_goals(goals_tokens or []),
        )
    raise ProviderError(f"unsupported artifact type: {artifact_type.value}")


async def generate_artifact(
    ctx: dict[str, object],
    artifact_type_value: str,
    owner_id: int,
    job_id: str | None = None,
    goals: list[str] | None = None,
) -> str:
    """Generate an AI artifact from profile/job context and persist it.

    Returns the created artifact's id. arq retries on ProviderError so
    transient provider failures redeliver the job automatically.
    """
    settings = get_settings()
    store = build_store(settings.redis_url)
    artifact_type = ArtifactType(artifact_type_value)

    profile = await store.profiles.get(owner_id)
    job = await store.jobs.get(job_id) if job_id else None
    company_name = ""
    if job is not None:
        company = await store.companies.get(job.company_id)
        if company is not None:
            company_name = company.name
    context = await _build_context(
        artifact_type, profile, job, company_name, goals_tokens=goals
    )

    async with AsyncClient(timeout=60.0) as http_client:
        router = build_router(settings, http_client=http_client)
        text = await router.agenerate(artifact_type, context)

    artifact = Artifact(
        id=uuid4().hex[:8],
        type=artifact_type,
        owner_id=owner_id,
        origin=ArtifactOrigin.AI_GENERATED,
        text=text,
    )
    await store.artifacts.save(artifact)
    return artifact.id


class WorkerSettings:
    """arq entry point: `arq worker.main.WorkerSettings`."""

    functions = [generate_artifact]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
