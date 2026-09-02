"""Artifact commands: AI generation, redelivery, self-write, and upload."""

from __future__ import annotations

from typing import cast
from uuid import uuid4

from arq.connections import ArqRedis
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from domain.job import JobStatus
from telegram import Update
from telegram.ext import ContextTypes

from .common import get_store, require_company, require_employer, require_seeker, user_id

_TYPE_CHOICES = ", ".join(t.value for t in ArtifactType)


def _artifact_type(value: str) -> ArtifactType | None:
    try:
        return ArtifactType(value)
    except ValueError:
        return None


async def _enqueue(
    context: ContextTypes.DEFAULT_TYPE,
    artifact_type: ArtifactType,
    owner_id: int,
    job_id: str | None = None,
) -> bool:
    """Enqueue an AI generation job on the arq pool, if one is wired up."""
    pool = cast(ArqRedis | None, context.bot_data.get("arq"))
    if pool is None:
        return False
    await pool.enqueue_job(  # type: ignore[misc]
        "generate_artifact", artifact_type.value, owner_id, job_id=job_id
    )
    return True


async def _enqueue_or_warn(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    artifact_type: ArtifactType,
    owner_id: int,
    job_id: str | None = None,
) -> bool:
    """Try to enqueue; send a warning and return False if the worker is offline."""
    if await _enqueue(context, artifact_type, owner_id, job_id):
        return True
    assert update.effective_chat is not None
    await update.effective_chat.send_message(
        "The generation service isn't available. Try again shortly."
    )
    return False


async def coverletter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /coverletter <job_id>")
        return
    store = get_store(context)
    assert store is not None
    owner_id = user_id(update)
    job = await store.jobs.get(args[0])
    if job is None or job.status != JobStatus.PUBLISHED:
        await update.effective_chat.send_message(
            f"Job `{args[0]}` is not open for applications."
        )
        return
    if await store.profiles.get(owner_id) is None:
        await update.effective_chat.send_message(
            "Build your Seeker Profile first with /profile."
        )
        return
    if not await _enqueue_or_warn(update, context, ArtifactType.COVER_LETTER, owner_id, job.id):
        return
    await update.effective_chat.send_message(
        f"✍️ Cover letter queued for **{job.title}**. Check /artifacts in a moment."
    )


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_seeker(update, context):
        return
    store = get_store(context)
    assert store is not None
    owner_id = user_id(update)
    args = context.args or []
    job_id = None
    if args:
        job = await store.jobs.get(args[0])
        if job is None or job.status != JobStatus.PUBLISHED:
            await update.effective_chat.send_message(
                f"Job `{args[0]}` is not open for applications."
            )
            return
        job_id = job.id
    if await store.profiles.get(owner_id) is None:
        await update.effective_chat.send_message(
            "Build your Seeker Profile first with /profile."
        )
        return
    if not await _enqueue_or_warn(update, context, ArtifactType.RESUME, owner_id, job_id):
        return
    await update.effective_chat.send_message(
        "📄 Resume generation queued. Check /artifacts in a moment."
    )


async def refinejd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    if not await require_employer(update, context):
        return
    company = await require_company(update, context)
    if company is None:
        return
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /refinejd <job_id>")
        return
    store = get_store(context)
    assert store is not None
    owner_id = user_id(update)
    job = await store.jobs.get(args[0])
    if job is None or job.company_id != company.id:
        await update.effective_chat.send_message(
            f"No job `{args[0]}` in your company."
        )
        return
    if not await _enqueue_or_warn(update, context, ArtifactType.JOB_DESCRIPTION, owner_id, job.id):
        return
    await update.effective_chat.send_message(
        f"📝 Job description queued for **{job.title}**. Check /artifacts in a moment."
    )


async def artifacts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    store = get_store(context)
    assert store is not None
    owned = await store.artifacts.list_by_owner(user_id(update))
    if not owned:
        await update.effective_chat.send_message(
            "You have no artifacts yet. Generate one with /coverletter, "
            "/resume, or /refinejd."
        )
        return
    ordered = sorted(owned, key=lambda a: a.created_at)
    lines = [
        f"`{a.id}` · **{a.type.value}** · {a.origin.value} · "
        f"{a.created_at:%Y-%m-%d %H:%M}"
        for a in ordered
    ]
    await update.effective_chat.send_message("**Your artifacts:**\n" + "\n".join(lines))


async def artifact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /artifact <artifact_id>")
        return
    store = get_store(context)
    assert store is not None
    stored = await store.artifacts.get(args[0])
    if stored is None or stored.owner_id != user_id(update):
        await update.effective_chat.send_message(
            f"Artifact `{args[0]}` not found."
        )
        return
    if stored.origin == ArtifactOrigin.USER_UPLOADED:
        assert stored.storage_key is not None
        await update.effective_chat.send_document(
            stored.storage_key, caption=f"{stored.type.value} artifact"
        )
        return
    await update.effective_chat.send_message(
        f"📄 **{stored.type.value}** ({stored.origin.value})\n\n{stored.text}"
    )


async def write(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    args = context.args or []
    if len(args) < 2:
        await update.effective_chat.send_message(
            f"Usage: /write <{_TYPE_CHOICES}> <text>"
        )
        return
    artifact_type = _artifact_type(args[0])
    if artifact_type is None:
        await update.effective_chat.send_message(
            f"Artifact type must be one of: {_TYPE_CHOICES}"
        )
        return
    text = " ".join(args[1:]).strip()
    stored = Artifact(
        id=uuid4().hex[:8],
        type=artifact_type,
        owner_id=user_id(update),
        origin=ArtifactOrigin.USER_WRITTEN,
        text=text,
    )
    store = get_store(context)
    assert store is not None
    await store.artifacts.save(stored)
    await update.effective_chat.send_message(
        f"✏️ {artifact_type.value} saved as **{stored.id}**."
    )


async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    args = context.args or []
    if not args:
        await update.effective_chat.send_message(
            f"Usage: /upload <{_TYPE_CHOICES}> with an attached document"
        )
        return
    artifact_type = _artifact_type(args[0])
    if artifact_type is None:
        await update.effective_chat.send_message(
            f"Artifact type must be one of: {_TYPE_CHOICES}"
        )
        return
    document = update.message.document if update.message else None
    if document is None:
        await update.effective_chat.send_message(
            "Attach a document to your /upload message."
        )
        return
    stored = Artifact(
        id=uuid4().hex[:8],
        type=artifact_type,
        owner_id=user_id(update),
        origin=ArtifactOrigin.USER_UPLOADED,
        storage_key=document.file_id,
    )
    store = get_store(context)
    assert store is not None
    await store.artifacts.save(stored)
    await update.effective_chat.send_message(
        f"📎 {artifact_type.value} uploaded as **{stored.id}**."
    )
