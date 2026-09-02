"""Config-driven provider selection per artifact type."""

from __future__ import annotations

from collections.abc import Iterable

from domain.artifact import ArtifactType
from shared.config import Settings

from .prompts import ArtifactContext, build_prompt, system_prompt
from .providers import Provider, ProviderError

_PROVIDER_FIELD: dict[ArtifactType, str] = {
    ArtifactType.COVER_LETTER: "cover_letter_provider",
    ArtifactType.RESUME: "resume_provider",
    ArtifactType.JOB_DESCRIPTION: "job_description_provider",
}


class ProviderRouter:
    """Route each artifact type to its configured LLM provider.

    The mapping of artifact type -> provider is read from configuration
    (Settings), not hard-coded, so providers can be swapped or added without
    changing callers. This class is the AI seam consumers depend on.
    """

    def __init__(self, settings: Settings, providers: Iterable[Provider]) -> None:
        self._settings = settings
        self._by_id = {provider.id: provider for provider in providers}

    def provider_for(self, artifact_type: ArtifactType) -> Provider:
        by_id = self._by_id
        if not by_id:
            raise ProviderError(
                f"no providers configured for artifact type {artifact_type.value}"
            )
        configured = getattr(self._settings, _PROVIDER_FIELD[artifact_type], "auto")
        if configured == "auto":
            return next(iter(by_id.values()))
        provider = by_id.get(configured)
        if provider is None:
            raise ProviderError(
                f"provider {configured!r} is not configured for "
                f"artifact type {artifact_type.value}"
            )
        return provider

    async def agenerate(self, artifact_type: ArtifactType, context: ArtifactContext) -> str:
        provider = self.provider_for(artifact_type)
        return await provider.generate(
            system_prompt(), build_prompt(artifact_type, context)
        )
