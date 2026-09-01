from __future__ import annotations

from typing import Callable

from domain.application import Application, ApplicationError
from telegram import Update
from telegram.ext import ContextTypes

from .common import get_store, require_company, require_employer, user_id


async def _company_job_id(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> str | None:
    """Resolve the job a company member is reviewing, messaging on failure."""
    assert update.effective_chat is not None
    company = await require_company(update, context)
    if company is None:
        return None
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /applications <job_id>")
        return None
    job_id = args[0]
    store = get_store(context)
    assert store is not None
    job = await store.jobs.get(job_id)
    if job is None or job.company_id != company.id:
        await update.effective_chat.send_message(
            f"No job `{job_id}` in your company."
        )
        return None
    return job_id


async def applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_employer(update, context):
        return
    job_id = await _company_job_id(update, context)
    if job_id is None:
        return
    store = get_store(context)
    assert store is not None
    job = await store.jobs.get(job_id)
    assert job is not None
    apps = await store.applications.list_by_job(job_id)
    if not apps:
        await update.effective_chat.send_message(
            f"No applications for **{job.title}** yet."
        )
        return
    lines = [
        f"`{a.id}` · seeker `{a.seeker_id}` · {a.status.value}" for a in apps
    ]
    await update.effective_chat.send_message(
        f"**{job.title}** applications:\n" + "\n".join(lines)
    )


async def _application_transition(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    verb: str,
    transition: Callable[[Application], None],
) -> None:
    assert update.effective_chat is not None
    if not await require_employer(update, context):
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message(f"Usage: /{verb} <application_id>")
        return
    application_id = args[0]
    store = get_store(context)
    assert store is not None
    application = await store.applications.get(application_id)
    if application is None:
        await update.effective_chat.send_message(
            f"Application `{application_id}` not found."
        )
        return
    job = await store.jobs.get(application.job_id)
    if job is None:
        await update.effective_chat.send_message(
            f"Application `{application_id}` references a missing job."
        )
        return
    company = await store.companies.find_by_member(user_id(update))
    if company is None or job.company_id != company.id:
        await update.effective_chat.send_message(
            f"Application `{application_id}` is not for a job in your company."
        )
        return
    if not application.is_active:
        await update.effective_chat.send_message(
            f"Application `{application_id}` is already "
            f"{application.status.value} and can't be {verb}."
        )
        return
    try:
        transition(application)
    except ApplicationError as exc:
        await update.effective_chat.send_message(f"Cannot {verb}: {exc}")
        return
    await store.applications.save(application)
    await update.effective_chat.send_message(
        f"Application **{application_id}** is now `{application.status.value}`."
    )


async def review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _application_transition(
        update, context, "review", Application.start_review
    )


async def shortlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _application_transition(
        update, context, "shortlist", Application.shortlist
    )


async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _application_transition(update, context, "accept", Application.accept)


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _application_transition(update, context, "reject", Application.reject)
