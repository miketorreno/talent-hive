from __future__ import annotations

from typing import Optional, cast

from domain.identities import Role, User
from shared.store import Store
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

WELCOME = (
    "👋 Welcome to Talent Hive — the AI-powered job board.\n\n"
    "Pick your role to get started. You can hold both roles at once."
)

ROLE_MARKUP = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Employer", callback_data="role:employer"),
            InlineKeyboardButton("Job Seeker", callback_data="role:job_seeker"),
        ],
        [InlineKeyboardButton("I'm both", callback_data="role:both")],
    ]
)

_CHOICE_LABEL = {
    Role.EMPLOYER: "Employer",
    Role.JOB_SEEKER: "Job Seeker",
}

_SINGLE_ROLE: dict[str, Role] = {
    "role:employer": Role.EMPLOYER,
    "role:job_seeker": Role.JOB_SEEKER,
}


def _labels(roles: set[Role]) -> str:
    return ", ".join(_CHOICE_LABEL[r] for r in sorted(roles, key=lambda r: r.value))


async def _store(context: ContextTypes.DEFAULT_TYPE) -> Optional[Store]:
    return cast(Optional[Store], context.bot_data.get("store"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.effective_chat is not None
    user = update.effective_user
    assert user is not None
    existing = None
    store = await _store(context)
    if store is not None:
        existing = await store.users.get(user.id)
    roles = existing.roles if existing else frozenset()
    if roles:
        await update.effective_chat.send_message(
            f"You are registered as: {_labels(set(roles))}."
        )
    else:
        await update.effective_chat.send_message(WELCOME, reply_markup=ROLE_MARKUP)


async def on_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.callback_query is not None
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    assert user is not None

    data = query.data or ""
    if data == "role:both":
        roles = {Role.EMPLOYER, Role.JOB_SEEKER}
    elif data in _SINGLE_ROLE:
        roles = {_SINGLE_ROLE[data]}
    else:
        roles = set()

    store = await _store(context)
    if store is not None and roles:
        account = await store.users.get(user.id) or User(telegram_id=user.id)
        for role in roles:
            account = account.add_role(role)
        await store.users.save(account)

    await query.edit_message_text(
        f"You're all set as **{_labels(roles)}**!", parse_mode=ParseMode.MARKDOWN
    )
