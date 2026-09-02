"""Provider-agnostic LLM abstraction and concrete HTTP-backed providers.

The `Provider` interface is the AI seam: callers depend on it, never on a
specific vendor. Providers are added/configured without touching callers.
"""

from __future__ import annotations

import abc

from httpx import AsyncClient

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GOOGLE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

GROQ_MODEL = "llama-3.3-70b-versatile"
GOOGLE_MODEL = "gemini-1.5-flash"


class ProviderError(RuntimeError):
    """Raised when an LLM provider call fails."""


class Provider(abc.ABC):
    """Async LLM provider seam."""

    #: Stable identifier used for config-driven routing.
    id: str = ""

    @abc.abstractmethod
    async def generate(self, system: str, user: str) -> str:
        """Generate text from a system and user prompt."""


class GroqProvider(Provider):
    """Provider backed by the Groq OpenAI-compatible API."""

    id = "groq"

    def __init__(
        self,
        api_key: str,
        model: str = GROQ_MODEL,
        client: AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    async def generate(self, system: str, user: str) -> str:
        if not self._api_key:
            raise ProviderError(
                "Groq is not configured: set TH_GROQ_API_KEY"
            )
        if self._client is None:
            raise ProviderError("GroqProvider is not connected to an HTTP client")
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
        }
        response = await self._client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected Groq response shape") from None


class GoogleProvider(Provider):
    """Provider backed by the Google AI Studio (Gemini) API."""

    id = "google"

    def __init__(
        self,
        api_key: str,
        model: str = GOOGLE_MODEL,
        client: AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    async def generate(self, system: str, user: str) -> str:
        if not self._api_key:
            raise ProviderError(
                "Google AI Studio is not configured: set TH_GOOGLE_AI_API_KEY"
            )
        if self._client is None:
            raise ProviderError(
                "GoogleProvider is not connected to an HTTP client"
            )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user},
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system},
                ]
            },
            "generationConfig": {"temperature": 0.7},
        }
        response = await self._client.post(
            GOOGLE_URL.format(model=self._model),
            params={"key": self._api_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            raise ProviderError("unexpected Google response shape") from None
