"""Talent Hive ai package: provider-agnostic LLM abstraction."""

from .factory import build_router
from .prompts import ArtifactContext, build_prompt, system_prompt
from .providers import (
    GoogleProvider,
    GroqProvider,
    Provider,
    ProviderError,
)
from .router import ProviderRouter

__all__ = [
    "Provider",
    "ProviderError",
    "GroqProvider",
    "GoogleProvider",
    "ProviderRouter",
    "build_router",
    "ArtifactContext",
    "build_prompt",
    "system_prompt",
]
