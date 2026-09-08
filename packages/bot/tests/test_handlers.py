import pytest
from _bot_helpers import (
    FakeCallbackQuery,
    FakeContext,
    FakeUpdate,
    make_store,
    register,
    register_employer,
)
from bot.handlers import ROLE_MARKUP, on_role, start
from bot.seekers import profile
from domain.identities import Role


@pytest.mark.asyncio
async def test_start_prompts_new_user_to_pick_a_role() -> None:
    store = make_store()
    update = FakeUpdate(7)

    await start(update, FakeContext(store))  # type: ignore[arg-type]

    message = update.effective_chat.messages[-1]
    assert "Pick your role to get started" in message
    labels = [
        button.text
        for row in ROLE_MARKUP.inline_keyboard
        for button in row
    ]
    assert "Employer" in labels
    assert "Job Seeker" in labels
    assert "I'm both" in labels
    assert update.effective_chat.last_reply_markup is ROLE_MARKUP


@pytest.mark.asyncio
async def test_start_shows_roles_for_existing_user() -> None:
    store = make_store()
    await register_employer(store, 7)
    update = FakeUpdate(7)

    await start(update, FakeContext(store))  # type: ignore[arg-type]

    assert "You are registered as: Employer." in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_start_shows_both_roles_for_existing_user() -> None:
    store = make_store()
    await register(store, 7, Role.EMPLOYER)
    await register(store, 7, Role.JOB_SEEKER)
    update = FakeUpdate(7)

    await start(update, FakeContext(store))  # type: ignore[arg-type]

    assert (
        "You are registered as: Employer, Job Seeker."
        in update.effective_chat.messages[-1]
    )


@pytest.mark.asyncio
async def test_on_role_employer_registers_user_as_employer() -> None:
    store = make_store()
    update = FakeUpdate(7, callback_query=FakeCallbackQuery("role:employer"))

    await on_role(update, FakeContext(store))  # type: ignore[arg-type]

    user = await store.users.get(7)
    assert user is not None
    assert user.is_employer
    assert not user.is_job_seeker
    assert "You're all set as **Employer**!" in update.callback_query.edited[-1]  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_on_role_job_seeker_registers_user_as_seeker() -> None:
    store = make_store()
    update = FakeUpdate(7, callback_query=FakeCallbackQuery("role:job_seeker"))

    await on_role(update, FakeContext(store))  # type: ignore[arg-type]

    user = await store.users.get(7)
    assert user is not None
    assert user.is_job_seeker
    assert not user.is_employer


@pytest.mark.asyncio
async def test_on_role_both_registers_user_with_both_roles() -> None:
    store = make_store()
    update = FakeUpdate(7, callback_query=FakeCallbackQuery("role:both"))

    await on_role(update, FakeContext(store))  # type: ignore[arg-type]

    user = await store.users.get(7)
    assert user is not None
    assert user.is_employer
    assert user.is_job_seeker
    assert (
        "You're all set as **Employer, Job Seeker**!"
        in update.callback_query.edited[-1]  # type: ignore[union-attr]
    )


@pytest.mark.asyncio
async def test_on_role_unknown_data_does_not_register_user() -> None:
    store = make_store()
    update = FakeUpdate(7, callback_query=FakeCallbackQuery("role:unknown"))

    await on_role(update, FakeContext(store))  # type: ignore[arg-type]

    assert await store.users.get(7) is None


@pytest.mark.asyncio
async def test_picking_employer_blocks_seeker_only_flows() -> None:
    store = make_store()
    update = FakeUpdate(7, callback_query=FakeCallbackQuery("role:employer"))

    await on_role(update, FakeContext(store))  # type: ignore[arg-type]

    seeker_update = FakeUpdate(7)
    await profile(seeker_update, FakeContext(store))  # type: ignore[arg-type]

    user = await store.users.get(7)
    assert user is not None
    assert user.is_employer
    assert not user.is_job_seeker
    assert "Job Seeker role" in seeker_update.effective_chat.messages[-1]
