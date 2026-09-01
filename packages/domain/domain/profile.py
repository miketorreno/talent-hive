from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ._time import now_utc
from .errors import DomainError


class ProfileError(DomainError):
    """Raised when a Seeker Profile violates a domain rule."""


@dataclass
class SeekerProfile:
    """The Job Seeker's stored skills, experience, and background.

    Used as the template base for generating artifacts.
    """

    seeker_id: int
    skills: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    background: str = ""
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if any(not skill.strip() for skill in self.skills):
            raise ProfileError("skills cannot be blank")
        if any(not item.strip() for item in self.experience):
            raise ProfileError("experience entries cannot be blank")

    @property
    def is_complete(self) -> bool:
        return bool(self.skills) and bool(self.background)

    def add_skill(self, skill: str) -> None:
        skill = skill.strip()
        if not skill:
            raise ProfileError("skill cannot be blank")
        if skill not in self.skills:
            self.skills.append(skill)
            self._touch()

    def add_experience(self, item: str) -> None:
        item = item.strip()
        if not item:
            raise ProfileError("experience cannot be blank")
        self.experience.append(item)
        self._touch()

    def set_background(self, background: str) -> None:
        if not background.strip():
            raise ProfileError("background cannot be blank")
        self.background = background
        self._touch()

    def _touch(self) -> None:
        self.updated_at = now_utc()
