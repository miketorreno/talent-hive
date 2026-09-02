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


class CompanyRegistry:
    """Owns the companies known to the system.

    Enforces the domain rule that an employer holds exactly one company: an
    owner cannot start or take ownership of a second company. Ownership is
    only ever changed through the registry so the invariant can never go stale.
    Company lookup is keyed by id.
    """

    def __init__(self) -> None:
        self._companies: dict[str, Company] = {}
        self._owner_to_company: dict[int, str] = {}

    def add_company(self, company: Company) -> None:
        if company.id in self._companies:
            raise CompanyError(f"a company with id {company.id!r} already exists")
        if company.owner_id is not None:
            self._enforce_one_company_per_owner(company.owner_id, company.id)
        self._companies[company.id] = company
        if company.owner_id is not None:
            self._owner_to_company[company.owner_id] = company.id

    def set_owner(self, company_id: str, owner_id: int) -> None:
        """Make ``owner_id`` the owner of an already-registered company.

        The only supported way to (re)assign ownership, so the one-company
        rule is checked here rather than through direct ``Company`` mutation.
        """
        company = self._require(company_id)
        self._enforce_one_company_per_owner(owner_id, company_id)
        company.set_owner(owner_id)
        self._owner_to_company[owner_id] = company_id

    def get(self, company_id: str) -> Company | None:
        return self._companies.get(company_id)

    def _enforce_one_company_per_owner(self, owner_id: int, company_id: str) -> None:
        existing_id = self._owner_to_company.get(owner_id)
        if existing_id is not None and existing_id != company_id:
            raise CompanyError("an employer can hold exactly one company")

    def _require(self, company_id: str) -> Company:
        company = self._companies.get(company_id)
        if company is None:
            raise CompanyError(f"unknown company: {company_id!r}")
        return company
