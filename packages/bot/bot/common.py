from __future__ import annotations

from typing import cast

from domain.company import Company
from shared.store import Store
from telegram import Update
from telegram.ext import ContextTypes


def get_store(context: ContextTypes.DEFAULT_TYPE) -> Store | None:
    return cast(Store | None, context.bot_data.get("store"))


def user_id(update: Update) -> int:
    user = update.effective_user
    assert user is not None
    return user.id


async def require_employer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    store = get_store(context)
    if store is None:
        return False
    account = await store.users.get(user_id(update))
    if account is None or not account.is_employer:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "You need the Employer role. Send /start and pick Employer."
        )
        return False
    return True


async def require_seeker(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    store = get_store(context)
    if store is None:
        return False
    account = await store.users.get(user_id(update))
    if account is None or not account.is_job_seeker:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "You need the Job Seeker role. Send /start and pick Job Seeker."
        )
        return False
    return True


async def require_company(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Company | None:
    store = get_store(context)
    if store is None:
        return None
    company = await store.companies.find_by_member(user_id(update))
    if company is None:
        assert update.effective_chat is not None
        await update.effective_chat.send_message(
            "You are not part of any company. Use /company <name> to create one."
        )
    return company
