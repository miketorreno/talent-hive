"""Factory for wiring the AI router to configured providers."""

from __future__ import annotations

from httpx import AsyncClient
from shared.config import Settings

from .providers import GoogleProvider, GroqProvider, Provider
from .router import ProviderRouter


def build_router(settings: Settings, http_client: AsyncClient | None = None) -> ProviderRouter:
    """Construct a router from settings and an optional shared HTTP client."""
    providers: list[Provider] = []
    if settings.groq_api_key:
        providers.append(GroqProvider(settings.groq_api_key, client=http_client))
    if settings.google_ai_api_key:
        providers.append(GoogleProvider(settings.google_ai_api_key, client=http_client))
    return ProviderRouter(settings, providers)
