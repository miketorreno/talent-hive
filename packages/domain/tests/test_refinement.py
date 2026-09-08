import pytest
from domain.refinement import (
    LengthTarget,
    RefinementGoal,
    RefinementGoals,
    RefinementGoalsError,
    parse_refinement_goals,
)


class TestRefinementGoals:
    def test_empty_goals_are_allowed(self):
        goals = RefinementGoals()
        assert goals.goals == frozenset()
        assert goals.length is LengthTarget.KEEP

    def test_select_goals_and_length(self):
        goals = RefinementGoals(
            goals=frozenset(
                {RefinementGoal.CLARITY, RefinementGoal.INCLUSIVITY}
            ),
            length=LengthTarget.SHORTER,
        )
        assert goals.goals == frozenset(
            {RefinementGoal.CLARITY, RefinementGoal.INCLUSIVITY}
        )
        assert goals.length is LengthTarget.SHORTER

    def test_has_goal(self):
        goals = RefinementGoals(
            goals=frozenset({RefinementGoal.SKILLS_EMPHASIS})
        )
        assert goals.has_goal(RefinementGoal.SKILLS_EMPHASIS)
        assert not goals.has_goal(RefinementGoal.CLARITY)

    def test_invalid_goal_value_rejected(self):
        with pytest.raises(RefinementGoalsError):
            RefinementGoals(goals={"nonsense"})  # type: ignore[arg-type]

    def test_invalid_length_value_rejected(self):
        with pytest.raises(RefinementGoalsError):
            RefinementGoals(length="nope")  # type: ignore[arg-type]

    def test_renders_shorter_version_of_length(self):
        goals = RefinementGoals(
            goals=frozenset({RefinementGoal.CLARITY}),
            length=LengthTarget.SHORTER,
        )
        text = goals.to_prompt_text()
        assert "clearer" in text
        assert "shorter" in text


class TestParseRefinementGoals:
    def test_parses_goal_words(self):
        goals = parse_refinement_goals(["clarity", "inclusivity", "skills"])
        assert goals.goals == frozenset(
            {RefinementGoal.CLARITY, RefinementGoal.INCLUSIVITY, RefinementGoal.SKILLS_EMPHASIS}
        )

    def test_parses_length_words(self):
        assert parse_refinement_goals(["shorter"]).length is LengthTarget.SHORTER
        assert parse_refinement_goals(["longer"]).length is LengthTarget.LONGER
        assert parse_refinement_goals(["keep"]).length is LengthTarget.KEEP

    def test_skills_emphasis_spelling_is_accepted(self):
        goals = parse_refinement_goals(["skills_emphasis"])
        assert goals.goals == frozenset({RefinementGoal.SKILLS_EMPHASIS})

    def test_empty_input_yields_defaults(self):
        goals = parse_refinement_goals([])
        assert goals.goals == frozenset()
        assert goals.length is LengthTarget.KEEP

    def test_unknown_keywords_are_ignored(self):
        goals = parse_refinement_goals(["clarity", "bogus", "shorter"])
        assert goals.goals == frozenset({RefinementGoal.CLARITY})
        assert goals.length is LengthTarget.SHORTER
