from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .company import EmployerRole


class RoleError(ValueError):
    """Raised when a user-role operation violates a domain rule."""


class Role(str, Enum):
    """The roles a user can hold.

    A user can hold both the EMPLOYER and the JOB_SEEKER role; the two are
    not mutually exclusive.
    """

    EMPLOYER = "employer"
    JOB_SEEKER = "job_seeker"


@dataclass(frozen=True)
class User:
    """The sole identity in the system: a Telegram user ID."""

    telegram_id: int
    roles: frozenset[Role] = field(default_factory=frozenset)

    @property
    def is_employer(self) -> bool:
        return Role.EMPLOYER in self.roles

    @property
    def is_job_seeker(self) -> bool:
        return Role.JOB_SEEKER in self.roles

    def add_role(self, role: Role) -> "User":
        if role not in Role:
            raise RoleError(f"unknown role: {role}")
        return User(self.telegram_id, self.roles | {role})

    def remove_role(self, role: Role) -> "User":
        return User(self.telegram_id, self.roles - {role})


@dataclass(frozen=True)
class EmployerMembership:
    """How an Employer relates to a Company: as an Owner or a Recruiter."""

    user_id: int
    company_id: str
    role: EmployerRole
