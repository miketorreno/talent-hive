"""Talent Hive worker package: arq consumer for AI generation jobs."""

from .main import WorkerSettings, generate_artifact

__all__ = ["WorkerSettings", "generate_artifact"]
