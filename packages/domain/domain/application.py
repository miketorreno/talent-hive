from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ._time import now_utc
from .errors import DomainError


class ApplicationStatus(str, Enum):
    """State of an Application through the review workflow."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationError(DomainError):
    """Raised when an application transition is invalid."""


# Allowed transitions for the Application state machine.
# Withdrawn is seeker-initiated; at any active state a seeker may withdraw.
_TRANSITIONS: dict[ApplicationStatus, frozenset[ApplicationStatus]] = {
    ApplicationStatus.SUBMITTED: frozenset(
        {ApplicationStatus.UNDER_REVIEW, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.UNDER_REVIEW: frozenset(
        {ApplicationStatus.SHORTLISTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.SHORTLISTED: frozenset(
        {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}
    ),
    ApplicationStatus.ACCEPTED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


@dataclass
class Application:
    """A job seeker's submission to a specific job."""

    id: str
    job_id: str
    seeker_id: int
    status: ApplicationStatus = ApplicationStatus.SUBMITTED
    cover_letter: str = ""
    created_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if not isinstance(self.status, ApplicationStatus):
            raise ApplicationError(f"invalid application status: {self.status!r}")

    def transition(self, target: ApplicationStatus) -> None:
        if target not in _TRANSITIONS[self.status]:
            raise ApplicationError(
                f"cannot move an application from {self.status.value} to {target.value}"
            )
        self.status = target

    def start_review(self) -> None:
        self.transition(ApplicationStatus.UNDER_REVIEW)

    def shortlist(self) -> None:
        self.transition(ApplicationStatus.SHORTLISTED)

    def accept(self) -> None:
        self.transition(ApplicationStatus.ACCEPTED)

    def reject(self) -> None:
        self.transition(ApplicationStatus.REJECTED)

    def withdraw(self) -> None:
        """Seeker-initiated withdrawal from any active state."""
        self.transition(ApplicationStatus.WITHDRAWN)

    @property
    def is_active(self) -> bool:
        return self.status not in (
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        )
