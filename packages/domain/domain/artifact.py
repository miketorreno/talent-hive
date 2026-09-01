from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ._time import now_utc
from .errors import DomainError


class ArtifactType(str, Enum):
    """What kind of document an Artifact is."""

    COVER_LETTER = "cover_letter"
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"


class ArtifactOrigin(str, Enum):
    """How an Artifact came to exist."""

    AI_GENERATED = "ai_generated"
    USER_WRITTEN = "user_written"
    USER_UPLOADED = "user_uploaded"


class ArtifactError(DomainError):
    """Raised when an artifact is malformed."""


@dataclass(frozen=True)
class Artifact:
    """A document that is AI-generated, user-written, or user-uploaded.

    Single concept tagged by type and carrying an origin. AI-generated and
    user-written artifacts hold text inline; user-uploaded artifacts hold a
    storage key referencing an S3 object.
    """

    type: ArtifactType
    owner_id: int
    origin: ArtifactOrigin
    text: str = ""
    storage_key: str | None = None
    created_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.type, ArtifactType):
            raise ArtifactError(f"invalid artifact type: {self.type!r}")
        if not isinstance(self.origin, ArtifactOrigin):
            raise ArtifactError(f"invalid artifact origin: {self.origin!r}")
        if self.origin == ArtifactOrigin.USER_UPLOADED and not self.storage_key:
            raise ArtifactError("a user-uploaded artifact needs a storage key")
        if self.origin in (
            ArtifactOrigin.AI_GENERATED,
            ArtifactOrigin.USER_WRITTEN,
        ) and not self.text:
            raise ArtifactError("an in-line artifact needs text")
        if self.storage_key and self.origin != ArtifactOrigin.USER_UPLOADED:
            raise ArtifactError("a storage key is only valid for uploaded artifacts")
