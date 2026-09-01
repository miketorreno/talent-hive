from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import DomainError


class EmployerRole(str, Enum):
    """How an Employer is attached to a Company."""

    OWNER = "owner"
    RECRUITER = "recruiter"


class CompanyError(DomainError):
    """Raised when a company operation violates a domain rule."""


@dataclass
class Company:
    """An organization that offers jobs.

    Owned by an Owner; an Owner may add Recruiters who publish jobs on the
    company's behalf. An employer holds at most one company.
    """

    id: str
    name: str
    description: str = ""
    owner_id: int | None = None
    recruiter_ids: set[int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not self.name:
            raise CompanyError("a company needs a name")
        if self.recruiter_ids is None:
            self.recruiter_ids = set()

    def set_owner(self, owner_id: int) -> None:
        if self.owner_id is not None and self.owner_id != owner_id:
            raise CompanyError("a company already has an owner")
        self.owner_id = owner_id

    def add_recruiter(self, recruiter_id: int) -> None:
        # The owner is already a member; never duplicate them as a recruiter.
        if self.owner_id is not None and recruiter_id == self.owner_id:
            return
        self.recruiter_ids.add(recruiter_id)

    def remove_recruiter(self, recruiter_id: int) -> None:
        if recruiter_id == self.owner_id:
            raise CompanyError("the owner cannot be removed as a recruiter")
        self.recruiter_ids.discard(recruiter_id)

    def members(self) -> set[int]:
        members = set(self.recruiter_ids)
        if self.owner_id is not None:
            members.add(self.owner_id)
        return members

    def member_role(self, user_id: int) -> EmployerRole | None:
        if user_id == self.owner_id:
            return EmployerRole.OWNER
        if user_id in self.recruiter_ids:
            return EmployerRole.RECRUITER
        return None

    def is_member(self, user_id: int) -> bool:
        return self.member_role(user_id) is not None
