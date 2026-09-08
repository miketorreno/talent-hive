from __future__ import annotations

from uuid import uuid4

from domain.application import Application
from domain.job import Job, JobStatus
from domain.profile import ProfileError, SeekerProfile
from telegram import Update
from telegram.ext import ContextTypes

from .common import get_store, require_seeker, user_id

_HELP = (
    "Job seeker commands:\n"
    "/profile — show your Seeker Profile\n"
    "/addskill <skill> — add a skill to your profile\n"
    "/addexperience <text> — add an experience entry\n"
    "/background <text> — set your background\n"
    "/jobs — browse published jobs\n"
    "/search <query> — search published jobs\n"
    "/apply <job_id> — apply to a published job\n"
    "/myapps — list your applications\n"
    "/withdraw <application_id> — withdraw an application\n"
    "/coverletter <job_id> — AI-generate a cover letter for a job\n"
    "/resume [job_id] — AI-generate a resume, optionally tailored to a job\n"
    "/artifact <id> / /artifacts — revisit your artifacts\n"
    "/write <type> <text> — save an artifact you wrote\n"
    "/upload <type> + document — store an artifact file"
)


async def seeker_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    await update.effective_chat.send_message(_HELP)


async def _load_profile(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> SeekerProfile:
    store = get_store(context)
    assert store is not None
    seeker_id = user_id(update)
    profile = await store.profiles.get(seeker_id)
    if profile is None:
        profile = SeekerProfile(seeker_id=seeker_id)
        await store.profiles.save(profile)
    return profile


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    current = await _load_profile(update, context)
    skills = ", ".join(current.skills) or "—"
    experience = "\n".join(f"• {item}" for item in current.experience) or "—"
    completeness = "complete" if current.is_complete else "incomplete"
    await update.effective_chat.send_message(
        f"🎯 **Seeker Profile** ({completeness})\n\n"
        f"**Skills:** {skills}\n"
        f"**Experience:**\n{experience}\n"
        f"**Background:** {current.background or '—'}"
    )


async def add_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    skill = " ".join(args).strip()
    if not skill:
        await update.effective_chat.send_message("Usage: /addskill <skill>")
        return
    current = await _load_profile(update, context)
    try:
        current.add_skill(skill)
    except ProfileError as exc:
        await update.effective_chat.send_message(str(exc))
        return
    store = get_store(context)
    assert store is not None
    await store.profiles.save(current)
    await update.effective_chat.send_message(f"Skill **{skill}** added.")


async def add_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    item = " ".join(args).strip()
    if not item:
        await update.effective_chat.send_message(
            "Usage: /addexperience <text>"
        )
        return
    current = await _load_profile(update, context)
    try:
        current.add_experience(item)
    except ProfileError as exc:
        await update.effective_chat.send_message(str(exc))
        return
    store = get_store(context)
    assert store is not None
    await store.profiles.save(current)
    await update.effective_chat.send_message("Experience entry added.")


async def background(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    text = " ".join(args).strip()
    if not text:
        await update.effective_chat.send_message(
            "Usage: /background <your background>"
        )
        return
    current = await _load_profile(update, context)
    try:
        current.set_background(text)
    except ProfileError as exc:
        await update.effective_chat.send_message(str(exc))
        return
    store = get_store(context)
    assert store is not None
    await store.profiles.save(current)
    await update.effective_chat.send_message("Background saved.")


def _format_job(job: Job) -> str:
    return (
        f"`{job.id}` · **{job.title}**\n"
        f"{job.description}\n"
        f"Requirements: {job.requirements}"
    )


async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    store = get_store(context)
    assert store is not None
    published = await store.jobs.list_published()
    if not published:
        await update.effective_chat.send_message("No published jobs right now.")
        return
    ordered = sorted(published, key=lambda job: job.created_at)
    await update.effective_chat.send_message(
        "**Published jobs:**\n\n" + "\n\n".join(_format_job(job) for job in ordered)
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    query = " ".join(args).strip()
    if not query:
        await update.effective_chat.send_message("Usage: /search <query>")
        return
    store = get_store(context)
    assert store is not None
    matches = await store.jobs.search_published(query)
    if not matches:
        await update.effective_chat.send_message(
            f"No published jobs match **{query}**."
        )
        return
    ordered = sorted(matches, key=lambda job: job.created_at)
    await update.effective_chat.send_message(
        f"**Results for '{query}':**\n\n"
        + "\n\n".join(_format_job(job) for job in ordered)
    )


async def apply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /apply <job_id>")
        return
    job_id = args[0]
    store = get_store(context)
    assert store is not None
    job = await store.jobs.get(job_id)
    if job is None or job.status != JobStatus.PUBLISHED:
        await update.effective_chat.send_message(
            f"Job `{job_id}` is not open for applications."
        )
        return

    existing = await store.applications.list_by_seeker(user_id(update))
    if any(app.job_id == job_id for app in existing):
        await update.effective_chat.send_message(
            "You already applied to this job."
        )
        return

    application = Application(
        id=uuid4().hex[:8],
        job_id=job_id,
        seeker_id=user_id(update),
    )
    await store.applications.save(application)
    await update.effective_chat.send_message(
        f"✅ Application **{application.id}** submitted for **{job.title}**."
    )


async def my_applications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    store = get_store(context)
    assert store is not None
    applications = await store.applications.list_by_seeker(user_id(update))
    if not applications:
        await update.effective_chat.send_message(
            "You haven't applied to any jobs yet."
        )
        return
    lines = []
    for application in applications:
        job = await store.jobs.get(application.job_id)
        title = job.title if job else application.job_id
        lines.append(
            f"`{application.id}` · **{title}** · {application.status.value}"
        )
    await update.effective_chat.send_message(
        "**Your applications:**\n" + "\n".join(lines)
    )


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message(
            "Usage: /withdraw <application_id>"
        )
        return
    application_id = args[0]
    store = get_store(context)
    assert store is not None
    application = await store.applications.get(application_id)
    if application is None or application.seeker_id != user_id(update):
        await update.effective_chat.send_message(
            f"Application `{application_id}` not found."
        )
        return
    if not application.is_active:
        await update.effective_chat.send_message(
            f"Application `{application_id}` is already "
            f"{application.status.value} and can't be withdrawn."
        )
        return
    application.withdraw()
    await store.applications.save(application)
    await update.effective_chat.send_message(
        f"Application **{application_id}** withdrawn."
    )
