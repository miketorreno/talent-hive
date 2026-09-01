from __future__ import annotations

from typing import Callable, cast
from uuid import uuid4

from domain.company import Company
from domain.job import Job, JobError
from shared.store import Store
from telegram import Update
from telegram.ext import ContextTypes

_HELP = (
    "Employer commands:\n"
    "/company <name> — create your company (you become its Owner)\n"
    "/company — show your company\n"
    "/addrecruiter <user_id> — add an Employer as a Recruiter (Owner only)\n"
    "/newjob <title> — create a draft job\n"
    "/setdescription <job_id> <text> — set a job's description\n"
    "/setrequirements <job_id> <text> — set a job's requirements\n"
    "/publish <job_id> — publish a job\n"
    "/close <job_id> — close a job\n"
    "/archive <job_id> — archive a closed job\n"
    "/myjobs — list your company's jobs"
)


async def _store(context: ContextTypes.DEFAULT_TYPE) -> Store | None:
    return cast(Store | None, context.bot_data.get("store"))


async def employer_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    await update.effective_chat.send_message(_HELP)


async def _user_id(update: Update) -> int:
    user = update.effective_user
    assert user is not None
    return user.id


async def _require_employer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    store = await _store(context)
    if store is None:
        return False
    account = await store.users.get(await _user_id(update))
    if account is None or not account.is_employer:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "You need the Employer role. Send /start and pick Employer."
        )
        return False
    return True


async def _require_company(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Company | None:
    store = await _store(context)
    if store is None:
        return None
    uid = await _user_id(update)
    company = await store.companies.find_by_member(uid)
    if company is None:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "You are not part of any company. Use /company <name> to create one."
        )
    return company


async def _require_owner(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Company | None:
    store = await _store(context)
    if store is None:
        return None
    uid = await _user_id(update)
    company = await store.companies.find_by_owner(uid)
    if company is None:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "Only an Owner can do that. You are not an Owner of a company."
        )
    return company


async def company(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    store = await _store(context)
    if store is None:
        await update.effective_chat.send_message("Store unavailable.")
        return

    args = context.args or []
    name = " ".join(args).strip()

    if not name:
        current = await store.companies.find_by_owner(await _user_id(update))
        if current is None:
            await update.effective_chat.send_message(
                "You don't have a company yet. Use /company <name> to create one."
            )
            return
        await _render_company(update, current, store)
        return

    uid = await _user_id(update)
    existing = await store.companies.find_by_owner(uid)
    if existing is not None:
        await update.effective_chat.send_message(
            f"You already own **{existing.name}**. An employer holds one company."
        )
        return

    company_id = uuid4().hex[:8]
    new_company = Company(id=company_id, name=name)
    new_company.set_owner(uid)
    await store.companies.save(new_company)
    await update.effective_chat.send_message(
        f"🏢 **{name}** created. You are now its **Owner**."
    )


async def add_recruiter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    company = await _require_owner(update, context)
    if company is None:
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /addrecruiter <user_id>")
        return
    try:
        recruiter_id = int(args[0])
    except ValueError:
        await update.effective_chat.send_message("That doesn't look like a user id.")
        return

    store = await _store(context)
    assert store is not None
    target = await store.users.get(recruiter_id)
    if target is None or not target.is_employer:
        await update.effective_chat.send_message(
            f"User **{recruiter_id}** isn't an Employer. "
            "Ask them to /start and pick Employer first."
        )
        return
    company.add_recruiter(recruiter_id)
    await store.companies.save(company)
    await update.effective_chat.send_message(
        f"Recruiter **{recruiter_id}** added to **{company.name}**."
    )


async def new_job(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await _require_employer(update, context):
        return
    company = await _require_company(update, context)
    if company is None:
        return
    args = context.args or []
    title = " ".join(args).strip()
    if not title:
        await update.effective_chat.send_message(
            "Usage: /newjob <title>\n\n"
            "Then set the description and requirements before publishing:\n"
            "/setdescription <job_id> <text>\n"
            "/setrequirements <job_id> <text>"
        )
        return

    store = await _store(context)
    assert store is not None
    job_id = uuid4().hex[:8]
    job = Job(
        id=job_id,
        company_id=company.id,
        title=title,
        description="",
        requirements="",
        created_by=await _user_id(update),
    )
    await store.jobs.save(job)
    await update.effective_chat.send_message(
        f"📄 Draft job **{title}** created (id `{job_id}`).\n\n"
        "Set its description and requirements, then /publish it."
    )


async def _company_job(
    update: Update, context: ContextTypes.DEFAULT_TYPE, command: str, min_args: int
) -> Job | None:
    """Resolve the job a company member is acting on, messaging on failure."""
    assert update.effective_chat is not None
    company = await _require_company(update, context)
    if company is None:
        return None
    args = context.args or []
    if len(args) < min_args:
        extra = " <text>" if min_args > 1 else ""
        await update.effective_chat.send_message(
            f"Usage: /{command} <job_id>{extra}"
        )
        return None
    job_id = args[0]
    store = await _store(context)
    assert store is not None
    job = await store.jobs.get(job_id)
    if job is None or job.company_id != company.id:
        await update.effective_chat.send_message(f"No job `{job_id}` in your company.")
        return None
    return job


async def set_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    job = await _company_job(update, context, "setdescription", min_args=2)
    if job is None:
        return
    job.description = " ".join((context.args or [])[1:]).strip()
    store = await _store(context)
    assert store is not None
    await store.jobs.save(job)
    await update.effective_chat.send_message(f"Description saved for job `{job.id}`.")


async def set_requirements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    job = await _company_job(update, context, "setrequirements", min_args=2)
    if job is None:
        return
    job.requirements = " ".join((context.args or [])[1:]).strip()
    store = await _store(context)
    assert store is not None
    await store.jobs.save(job)
    await update.effective_chat.send_message(f"Requirements saved for job `{job.id}`.")


async def _apply_job_transition(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    verb: str,
    transition: Callable[[Job], None],
) -> None:
    assert update.effective_chat is not None
    job = await _company_job(update, context, verb, min_args=1)
    if job is None:
        return
    try:
        transition(job)
    except JobError as exc:
        await update.effective_chat.send_message(f"Cannot {verb}: {exc}")
        return
    store = await _store(context)
    assert store is not None
    await store.jobs.save(job)
    await update.effective_chat.send_message(
        f"Job **{job.title}** is now `{job.status.value}`."
    )


async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _apply_job_transition(update, context, "publish", Job.publish)


async def close(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _apply_job_transition(update, context, "close", Job.close)


async def archive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _apply_job_transition(update, context, "archive", Job.archive)


async def my_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    company = await _require_company(update, context)
    if company is None:
        return
    store = await _store(context)
    assert store is not None
    jobs = await store.jobs.list_by_company(company.id)
    if not jobs:
        await update.effective_chat.send_message("No jobs yet. Use /newjob <title>.")
        return
    lines = [
        f"`{j.id}` · **{j.title}** · {j.status.value}" for j in jobs
    ]
    await update.effective_chat.send_message(
        f"**{company.name}** jobs:\n" + "\n".join(lines)
    )


async def _render_company(
    update: Update, company: Company, store: Store
) -> None:
    assert update.effective_chat is not None
    jobs = await store.jobs.list_by_company(company.id)
    members = [str(m) for m in sorted(company.members())]
    job_count = f"Jobs: {len(jobs)}"
    await update.effective_chat.send_message(
        f"🏢 **{company.name}**\n"
        f"Owner: `{company.owner_id}`\n"
        f"Members: {', '.join(members) or '—'}\n"
        f"{job_count}"
    )
