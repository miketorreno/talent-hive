from __future__ import annotations

import asyncio
import logging

from redis import asyncio as aioredis
from shared.config import get_settings
from shared.store import RedisUserRepository
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from .handlers import on_role, start

logging.basicConfig(level=logging.INFO)


def build_application(token: str, redis_url: str) -> Application:
    redis = aioredis.from_url(redis_url, decode_responses=False)
    store = RedisUserRepository(redis)

    app = Application.builder().token(token).build()
    app.bot_data["user_store"] = store
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_role, pattern="^role:"))
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
