"""Prompt templates for AI artifact generation."""

from __future__ import annotations

from dataclasses import dataclass

from domain.artifact import ArtifactType

SYSTEM_PROMPT = (
    "You write professional hiring documents for a job board called Talent Hive. "
    "Use the project vocabulary: Artifact (not Document), Job Seeker (not Candidate), "
    "Seeker Profile (not Candidate profile). "
    "Return only the document text, with no preamble, no commentary, and no "
    "enclosing quotes or code fences."
)

_COVER_LETTER_USER = (
    "Write a tailored cover letter for the following job, grounded in the "
    "job seeker's profile.\n\n"
    "JOB: {job_title} at {company_name}\n"
    "JOB DESCRIPTION:\n{description}\n"
    "REQUIREMENTS:\n{requirements}\n\n"
    "JOB SEEKER BACKGROUND:\n{background}\n\n"
    "JOB SEEKER SKILLS:\n{skills}\n\n"
    "JOB SEEKER EXPERIENCE:\n{experience}"
)

_RESUME_USER = (
    "Write a professional resume for the following job seeker, tailored to the "
    "target job if one is provided.\n\n"
    "TARGET JOB: {job_title}\n"
    "JOB SEEKER BACKGROUND:\n{background}\n\n"
    "JOB SEEKER SKILLS:\n{skills}\n\n"
    "JOB SEEKER EXPERIENCE:\n{experience}"
)

_JOB_DESCRIPTION_USER = (
    "Write a clear, attractive job description for the following vacancy.\n\n"
    "ROLE TITLE: {job_title}\n"
    "RAW DESCRIPTION:\n{description}\n"
    "REQUIREMENTS SO FAR:\n{requirements}"
)


@dataclass(frozen=True)
class ArtifactContext:
    """The inputs an artifact is generated from."""

    job_title: str = ""
    company_name: str = ""
    description: str = ""
    requirements: str = ""
    background: str = ""
    skills: str = ""
    experience: str = ""


def build_prompt(artifact_type: ArtifactType, context: ArtifactContext) -> str:
    """Return the user prompt for a given artifact type and context."""
    _prompts: dict[ArtifactType, str] = {
        ArtifactType.COVER_LETTER: _COVER_LETTER_USER,
        ArtifactType.RESUME: _RESUME_USER,
        ArtifactType.JOB_DESCRIPTION: _JOB_DESCRIPTION_USER,
    }
    return _prompts[artifact_type].format(**context.__dict__)


def system_prompt() -> str:
    return SYSTEM_PROMPT
