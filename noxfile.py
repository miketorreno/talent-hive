"""Nox task orchestration across the Talent Hive monorepo."""

from __future__ import annotations

from pathlib import Path

import nox

nox.options.sessions = ["test", "lint", "typecheck"]

PACKAGES = ["domain", "ai", "shared", "bot", "worker"]

PYTHON = "3.12"

# Third-party runtime deps pulled from PyPI (not the internal path deps).
RUNTIME_DEPS = [
    "pydantic",
    "pydantic-settings",
    "redis",
    "httpx",
    "python-telegram-bot",
    "arq",
]


def _install(session: nox.Session) -> None:
    specs = []
    for p in PACKAGES:
        specs.extend(["--no-deps", "-e", f"packages/{p}"])
    # Install the internal packages without deps (they feed each other), then
    # pull third-party runtime deps normally in a separate pip call.
    session.install(*specs, "--no-deps")
    session.install(*RUNTIME_DEPS)


@nox.session(python=PYTHON)
def test(session: nox.Session) -> None:
    _install(session)
    session.install("pytest", "pytest-asyncio")
    test_dirs = [str(p) for p in Path("packages").glob("*/tests") if p.is_dir()]
    if not test_dirs:
        session.skip("no test directories yet")
        return
    session.run("pytest", *test_dirs)


@nox.session(python=PYTHON)
def lint(session: nox.Session) -> None:
    session.install("ruff")
    session.run("ruff", "check", *[f"packages/{p}" for p in PACKAGES])


@nox.session(python=PYTHON)
def typecheck(session: nox.Session) -> None:
    _install(session)
    session.install("mypy")
    session.run("mypy", *[f"packages/{p}" for p in PACKAGES])
