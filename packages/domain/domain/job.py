from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ._time import now_utc
from .errors import DomainError


class JobStatus(str, Enum):
    """State of a Job through its lifecycle."""

    DRAFT = "draft"
    PUBLISHED = "published"
    EXPIRED = "expired"
    CLOSED = "closed"
    ARCHIVED = "archived"


class JobError(DomainError):
    """Raised when a job state transition is invalid."""


# Allowed transitions for the Job state machine.
_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.DRAFT: frozenset({JobStatus.PUBLISHED, JobStatus.CLOSED}),
    JobStatus.PUBLISHED: frozenset({JobStatus.EXPIRED, JobStatus.CLOSED}),
    JobStatus.EXPIRED: frozenset({JobStatus.PUBLISHED, JobStatus.CLOSED, JobStatus.ARCHIVED}),
    JobStatus.CLOSED: frozenset({JobStatus.ARCHIVED}),
    JobStatus.ARCHIVED: frozenset(),
}

# A job may only be published if it is complete enough to be browsed.
_REQUIRED_FOR_PUBLISH = ("title", "description", "requirements")

# Fields a free-text search can match on.
_SEARCHABLE_FIELDS = ("title", "description", "requirements")


def search_terms(query: str) -> tuple[str, ...]:
    """Split a free-text query into lowercase terms to match against a Job.

    A Job matches when every returned term appears somewhere in its title,
    description, or requirements. Empty and whitespace-only queries yield no
    terms and therefore match nothing.
    """
    return tuple(term for term in query.lower().split() if term)


@dataclass
class Job:
    """A vacancy created by an employer for a company."""

    id: str
    company_id: str
    title: str
    description: str
    requirements: str = ""
    created_by: int | None = None
    status: JobStatus = JobStatus.DRAFT
    created_at: datetime = field(default_factory=now_utc)
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.title:
            raise JobError("a job needs a title")
        if not isinstance(self.status, JobStatus):
            raise JobError(f"invalid job status: {self.status!r}")

    def transition(self, target: JobStatus) -> None:
        if target not in _TRANSITIONS[self.status]:
            raise JobError(
                f"cannot move a job from {self.status.value} to {target.value}"
            )
        if target in (JobStatus.PUBLISHED,):
            self._validate_publishable()
        self.status = target

    def _validate_publishable(self) -> None:
        missing = [f for f in _REQUIRED_FOR_PUBLISH if not getattr(self, f)]
        if missing:
            raise JobError(f"cannot publish a job missing: {', '.join(missing)}")

    def publish(self) -> None:
        self.transition(JobStatus.PUBLISHED)

    def close(self) -> None:
        self.transition(JobStatus.CLOSED)

    def expire(self) -> None:
        self.transition(JobStatus.EXPIRED)

    def archive(self) -> None:
        self.transition(JobStatus.ARCHIVED)

    @property
    def is_active(self) -> bool:
        return self.status == JobStatus.PUBLISHED

    def matches(self, query: str) -> bool:
        """True when the Job matches every search term in the query."""
        terms = search_terms(query)
        if not terms:
            return False
        haystack = " ".join(
            getattr(self, field) for field in _SEARCHABLE_FIELDS
        ).lower()
        return all(term in haystack for term in terms)
