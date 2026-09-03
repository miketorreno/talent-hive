from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import DomainError


class RefinementGoal(str, Enum):
    """An aspect an employer asks the AI to focus on when refining a job description."""

    CLARITY = "clarity"
    INCLUSIVITY = "inclusivity"
    SKILLS_EMPHASIS = "skills_emphasis"


class LengthTarget(str, Enum):
    """How long the refined job description should be relative to the original."""

    SHORTER = "shorter"
    KEEP = "keep"
    LONGER = "longer"


class RefinementGoalsError(DomainError):
    """Raised when a RefinementGoals value is malformed."""


_LENGTH_WORDS: dict[str, LengthTarget] = {
    "shorter": LengthTarget.SHORTER,
    "keep": LengthTarget.KEEP,
    "longer": LengthTarget.LONGER,
}

_GOAL_WORDS: dict[str, RefinementGoal] = {
    "clarity": RefinementGoal.CLARITY,
    "inclusivity": RefinementGoal.INCLUSIVITY,
    "skills": RefinementGoal.SKILLS_EMPHASIS,
    "skills_emphasis": RefinementGoal.SKILLS_EMPHASIS,
}


def parse_refinement_goals(tokens: list[str]) -> "RefinementGoals":
    """Parse user-supplied keywords into a RefinementGoals value.

    Recognized goal words are "clarity", "inclusivity", and "skills" (or
    "skills_emphasis"); recognized length words are "shorter", "keep", and
    "longer". Unknown words are ignored. Each token is matched case-insensitively.
    """
    goals: set[RefinementGoal] = set()
    length = LengthTarget.KEEP
    for token in tokens:
        lowered = token.strip().lower()
        goal = _GOAL_WORDS.get(lowered)
        if goal is not None:
            goals.add(goal)
            continue
        target = _LENGTH_WORDS.get(lowered)
        if target is not None:
            length = target
    return RefinementGoals(goals=frozenset(goals), length=length)


@dataclass(frozen=True)
class RefinementGoals:
    """The aspects an employer asks the AI to focus on when refining a job description.

    Selected goals are among clarity, inclusivity, and skills emphasis, plus a
    length target of shorter, keep, or longer. An empty selection means the AI
    refines without specific direction beyond the shared system prompt.
    """

    goals: frozenset[RefinementGoal] = frozenset()
    length: LengthTarget = LengthTarget.KEEP

    def __post_init__(self) -> None:
        if any(not isinstance(goal, RefinementGoal) for goal in self.goals):
            raise RefinementGoalsError("invalid refinement goal")
        if not isinstance(self.length, LengthTarget):
            raise RefinementGoalsError("invalid length target")

    def has_goal(self, goal: RefinementGoal) -> bool:
        return goal in self.goals

    def to_prompt_text(self) -> str:
        """Render refinement goals as instructions for an LLM prompt."""
        lines: list[str] = []
        if self.goals:
            goal_text = {
                RefinementGoal.CLARITY: "make the description clearer",
                RefinementGoal.INCLUSIVITY: "make the language more inclusive",
                RefinementGoal.SKILLS_EMPHASIS: "emphasize the skills required",
            }
            goal_order = sorted(self.goals, key=lambda g: g.value)
            lines.append(
                "Refinement goals: "
                + "; ".join(goal_text[g] for g in goal_order)
                + "."
            )
        if self.length is not LengthTarget.KEEP:
            lines.append(f"Target length: {self.length.value} than the original description.")
        return " ".join(lines).strip()
