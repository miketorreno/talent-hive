import pytest
from ai.prompts import ArtifactContext, build_prompt, system_prompt
from ai.providers import GoogleProvider, Provider, ProviderError
from ai.router import ProviderRouter
from domain.artifact import ArtifactType
from shared.config import Settings


class FakeProvider(Provider):
    id = "fake"

    def __init__(self, responses: dict[ArtifactType, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return next(iter(self.responses.values()), "generated text")


class RoutingProvider(Provider):
    """A provider that records which artifact type's prompt it saw."""

    id = "routing"

    def __init__(self) -> None:
        self.seen: list[ArtifactType] = []

    async def generate(self, system: str, user: str) -> str:
        return "routing text"


def make_settings(**overrides) -> Settings:
    defaults = {
        "cover_letter_provider": "auto",
        "resume_provider": "auto",
        "job_description_provider": "auto",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_provider_for_routes_to_configured_provider() -> None:
    groq = FakeProvider()
    groq.id = "groq"
    google = FakeProvider()
    google.id = "google"
    router = ProviderRouter(make_settings(cover_letter_provider="groq"), [groq, google])
    assert router.provider_for(ArtifactType.COVER_LETTER) is groq


def test_provider_for_auto_uses_first_configured() -> None:
    groq = FakeProvider()
    groq.id = "groq"
    google = FakeProvider()
    google.id = "google"
    router = ProviderRouter(make_settings(), [groq, google])
    assert router.provider_for(ArtifactType.COVER_LETTER) is groq


def test_provider_for_unknown_type_raises() -> None:
    router = ProviderRouter(make_settings(), [])
    with pytest.raises(ProviderError):
        router.provider_for(ArtifactType.COVER_LETTER)


def test_provider_for_explicit_unconfigured_provider_raises() -> None:
    google = FakeProvider()
    google.id = "google"
    router = ProviderRouter(
        make_settings(cover_letter_provider="groq"), [google]
    )
    with pytest.raises(ProviderError, match="groq"):
        router.provider_for(ArtifactType.COVER_LETTER)


@pytest.mark.asyncio
async def test_agenerate_routes_through_configured_provider() -> None:
    groq = RoutingProvider()
    groq.id = "groq"
    google = RoutingProvider()
    google.id = "google"
    router = ProviderRouter(
        make_settings(cover_letter_provider="google"), [groq, google]
    )
    text = await router.agenerate(
        ArtifactType.COVER_LETTER,
        ArtifactContext(job_title="Engineer", description="d"),
    )
    assert text == "routing text"


@pytest.mark.asyncio
async def test_agenerate_builds_prompt_from_context() -> None:
    provider = FakeProvider()
    router = ProviderRouter(make_settings(), [provider])
    await router.agenerate(
        ArtifactType.COVER_LETTER,
        ArtifactContext(job_title="Engineer", background="5 yrs backend"),
    )
    system, user = provider.calls[0]
    assert "Engineer" in user
    assert "5 yrs backend" in user
    assert system == system_prompt()


def test_build_prompt_knows_all_artifact_types() -> None:
    for artifact_type in ArtifactType:
        prompt = build_prompt(
            artifact_type,
            ArtifactContext(job_title="Role", description="d", requirements="r"),
        )
        assert prompt


def test_job_description_prompt_includes_refinement_goals() -> None:
    from domain.refinement import LengthTarget, RefinementGoal, RefinementGoals

    goals = RefinementGoals(
        goals=frozenset({RefinementGoal.CLARITY, RefinementGoal.SKILLS_EMPHASIS}),
        length=LengthTarget.SHORTER,
    )
    prompt = build_prompt(
        ArtifactType.JOB_DESCRIPTION,
        ArtifactContext(
            job_title="Engineer", description="d", requirements="r",
            refinement_goals=goals,
        ),
    )
    assert "clearer" in prompt
    assert "skills" in prompt
    assert "shorter" in prompt


def test_job_description_prompt_without_goals_is_clean() -> None:
    prompt = build_prompt(
        ArtifactType.JOB_DESCRIPTION,
        ArtifactContext(job_title="Engineer", description="d", requirements="r"),
    )
    assert "REFINEMENT" not in prompt


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class FakeHttpClient:
    """Captures the last request payload for assertion."""

    def __init__(self, response_payload: dict) -> None:
        self._response = FakeResponse(response_payload)
        self.last_url: str = ""
        self.last_payload: dict = {}

    async def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.last_url = url
        self.last_payload = kwargs.get("json", {})  # type: ignore[assignment]
        return self._response


@pytest.mark.asyncio
async def test_google_provider_sends_system_instruction_separately() -> None:
    response_payload = {
        "candidates": [
            {"content": {"parts": [{"text": "  generated text  "}]}}
        ]
    }
    http = FakeHttpClient(response_payload)
    provider = GoogleProvider(api_key="test-key", client=http)  # type: ignore[arg-type]
    result = await provider.generate("You are a helper", "Write a resume")

    assert result == "generated text"
    payload = http.last_payload
    assert "systemInstruction" in payload
    assert payload["systemInstruction"] == {
        "parts": [{"text": "You are a helper"}]
    }
    contents = payload["contents"]
    assert len(contents) == 1
    assert contents[0]["parts"][0]["text"] == "Write a resume"
