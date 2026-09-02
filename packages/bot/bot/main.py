from __future__ import annotations

import asyncio
import logging

from arq.connections import RedisSettings, create_pool
from shared.config import get_settings
from shared.store import build_store
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from .applications import accept, applications, reject, review, shortlist
from .artifacts import (
    artifact,
    artifacts,
    coverletter,
    refinejd,
    resume,
    upload,
    write,
)
from .employers import (
    add_recruiter,
    archive,
    close,
    company,
    employer_help,
    my_jobs,
    new_job,
    publish,
    set_description,
    set_requirements,
)
from .handlers import on_role, start
from .seekers import (
    add_experience,
    add_skill,
    apply,
    background,
    jobs,
    my_applications,
    profile,
    search,
    seeker_help,
    withdraw,
)

logging.basicConfig(level=logging.INFO)


def build_application(token: str, redis_url: str) -> Application:
    store = build_store(redis_url)

    app = Application.builder().token(token).build()
    app.bot_data["store"] = store
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_role, pattern="^role:"))
    app.add_handler(CommandHandler("company", company))
    app.add_handler(CommandHandler("addrecruiter", add_recruiter))
    app.add_handler(CommandHandler("newjob", new_job))
    app.add_handler(CommandHandler("setdescription", set_description))
    app.add_handler(CommandHandler("setrequirements", set_requirements))
    app.add_handler(CommandHandler("publish", publish))
    app.add_handler(CommandHandler("close", close))
    app.add_handler(CommandHandler("archive", archive))
    app.add_handler(CommandHandler("myjobs", my_jobs))
    app.add_handler(CommandHandler("employer", employer_help))
    app.add_handler(CommandHandler("applications", applications))
    app.add_handler(CommandHandler("review", review))
    app.add_handler(CommandHandler("shortlist", shortlist))
    app.add_handler(CommandHandler("accept", accept))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("addskill", add_skill))
    app.add_handler(CommandHandler("addexperience", add_experience))
    app.add_handler(CommandHandler("background", background))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("apply", apply))
    app.add_handler(CommandHandler("myapps", my_applications))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("seeker", seeker_help))
    app.add_handler(CommandHandler("coverletter", coverletter))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("refinejd", refinejd))
    app.add_handler(CommandHandler("artifacts", artifacts))
    app.add_handler(CommandHandler("artifact", artifact))
    app.add_handler(CommandHandler("write", write))
    app.add_handler(CommandHandler("upload", upload))
    return app


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_token:
        raise SystemExit("TH_TELEGRAM_TOKEN is not set")
    app = build_application(settings.telegram_token, settings.redis_url)
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    app.bot_data["arq"] = pool
    await app.initialize()
    await app.start()
    assert app.updater is not None
    await app.updater.start_polling()
    await asyncio.Event().wait()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
