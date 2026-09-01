"""Talent Hive domain package.

Pure domain entities and state machines. This is the single behavioral test
seam: all behavior worth asserting lives here, free of I/O.
"""

from .application import Application, ApplicationStatus
from .artifact import Artifact, ArtifactOrigin, ArtifactType
from .company import Company, EmployerRole
from .identities import Role, User
from .job import Job, JobStatus
from .profile import SeekerProfile

__all__ = [
    "User",
    "Role",
    "Company",
    "EmployerRole",
    "Job",
    "JobStatus",
    "Application",
    "ApplicationStatus",
    "Artifact",
    "ArtifactType",
    "ArtifactOrigin",
    "SeekerProfile",
]
