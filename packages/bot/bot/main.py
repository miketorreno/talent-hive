from __future__ import annotations

import asyncio
import logging

from redis import asyncio as aioredis
from shared.config import get_settings
from shared.store import RedisCompanyRepository, RedisJobRepository, RedisUserRepository, Store
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

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

logging.basicConfig(level=logging.INFO)


def build_application(token: str, redis_url: str) -> Application:
    redis = aioredis.from_url(redis_url, decode_responses=False)
    store = Store(
        users=RedisUserRepository(redis),
        companies=RedisCompanyRepository(redis),
        jobs=RedisJobRepository(redis),
    )

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
    return app


async def main() -> None:
    settings = get_settings()
    if not settings.telegram_token:
        raise SystemExit("TH_TELEGRAM_TOKEN is not set")
    app = build_application(settings.telegram_token, settings.redis_url)
    await app.initialize()
    await app.start()
    assert app.updater is not None
    await app.updater.start_polling()
    await asyncio.Event().wait()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
