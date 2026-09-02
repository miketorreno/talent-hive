import pytest
from _bot_helpers import FakeContext, FakeUpdate, make_store, register_employer, register_seeker
from bot.applications import accept, applications, reject, review, shortlist
from bot.employers import company, new_job, publish, set_description, set_requirements
from bot.seekers import (
    add_experience,
    add_skill,
    apply,
    background,
    jobs,
    my_applications,
    profile,
    search,
    withdraw,
)


async def _publish_job(store, user_id: int, title: str) -> str:
    await register_employer(store, user_id)
    await company(FakeUpdate(user_id), FakeContext(store, ["Acme"]))  # type: ignore[arg-type]
    await new_job(FakeUpdate(user_id), FakeContext(store, [title]))  # type: ignore[arg-type]
    owner_company = await store.companies.find_by_owner(user_id)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]
    await set_description(FakeUpdate(user_id), FakeContext(store, [job.id, "Build things"]))  # type: ignore[arg-type]
    await set_requirements(FakeUpdate(user_id), FakeContext(store, [job.id, "Python"]))  # type: ignore[arg-type]
    await publish(FakeUpdate(user_id), FakeContext(store, [job.id]))  # type: ignore[arg-type]
    return job.id


@pytest.mark.asyncio
async def test_non_seeker_cannot_build_profile() -> None:
    store = make_store()
    await register_employer(store, 1)
    update = FakeUpdate(1)

    await add_skill(update, FakeContext(store, ["Python"]))  # type: ignore[arg-type]

    assert (await store.profiles.get(1)) is None
    assert "Job Seeker role" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_seeker_builds_profile() -> None:
    store = make_store()
    await register_seeker(store, 7)
    update = FakeUpdate(7)

    await add_skill(update, FakeContext(store, ["Python"]))  # type: ignore[arg-type]
    await add_experience(update, FakeContext(store, ["Built a bot"]))  # type: ignore[arg-type]
    await background(update, FakeContext(store, ["5 years backend"]))  # type: ignore[arg-type]

    loaded = await store.profiles.get(7)
    assert loaded is not None
    assert loaded.skills == ["Python"]
    assert loaded.experience == ["Built a bot"]
    assert loaded.background == "5 years backend"
    assert loaded.is_complete


@pytest.mark.asyncio
async def test_profile_shows_completeness() -> None:
    store = make_store()
    await register_seeker(store, 7)
    update = FakeUpdate(7)

    await profile(update, FakeContext(store))  # type: ignore[arg-type]

    assert "incomplete" in update.effective_chat.messages[-1]
    await add_skill(FakeUpdate(7), FakeContext(store, ["Python"]))  # type: ignore[arg-type]
    complete = FakeUpdate(7)
    await profile(complete, FakeContext(store))  # type: ignore[arg-type]
    assert "complete" in complete.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_browse_published_jobs_lists_only_published() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)

    update = FakeUpdate(7)
    await jobs(update, FakeContext(store))  # type: ignore[arg-type]

    message = update.effective_chat.messages[-1]
    assert job_id in message
    assert "Engineer" in message


@pytest.mark.asyncio
async def test_search_finds_published_job() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Backend Engineer")
    await register_seeker(store, 7)

    update = FakeUpdate(7)
    await search(update, FakeContext(store, ["backend"]))  # type: ignore[arg-type]

    message = update.effective_chat.messages[-1]
    assert job_id in message
    assert "Backend Engineer" in message


@pytest.mark.asyncio
async def test_search_requires_seeker_role() -> None:
    store = make_store()
    await register_employer(store, 1)

    update = FakeUpdate(1)
    await search(update, FakeContext(store, ["backend"]))  # type: ignore[arg-type]

    assert "Job Seeker role" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_search_with_no_query_shows_usage() -> None:
    store = make_store()
    await register_seeker(store, 7)

    update = FakeUpdate(7)
    await search(update, FakeContext(store))  # type: ignore[arg-type]

    assert "/search <query>" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_search_no_match_message() -> None:
    store = make_store()
    await _publish_job(store, 1, "Backend Engineer")
    await register_seeker(store, 7)

    update = FakeUpdate(7)
    await search(update, FakeContext(store, ["rust"]))  # type: ignore[arg-type]

    assert "No published jobs match" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_apply_to_published_job() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)

    update = FakeUpdate(7)
    await apply(update, FakeContext(store, [job_id]))  # type: ignore[arg-type]

    applications_for_job = await store.applications.list_by_job(job_id)
    assert len(applications_for_job) == 1
    assert applications_for_job[0].seeker_id == 7
    assert "submitted" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_cannot_apply_twice_to_same_job() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)

    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    second = FakeUpdate(7)
    await apply(second, FakeContext(store, [job_id]))  # type: ignore[arg-type]

    assert "already applied" in second.effective_chat.messages[-1]
    assert len(await store.applications.list_by_job(job_id)) == 1


@pytest.mark.asyncio
async def test_cannot_apply_to_unpublished_job() -> None:
    store = make_store()
    await register_seeker(store, 7)
    await register_employer(store, 1)
    await company(FakeUpdate(1), FakeContext(store, ["Acme"]))  # type: ignore[arg-type]
    await new_job(FakeUpdate(1), FakeContext(store, ["Engineer"]))  # type: ignore[arg-type]
    owner_company = await store.companies.find_by_owner(1)
    assert owner_company is not None
    job = (await store.jobs.list_by_company(owner_company.id))[0]

    update = FakeUpdate(7)
    await apply(update, FakeContext(store, [job.id]))  # type: ignore[arg-type]

    assert "not open" in update.effective_chat.messages[-1]
    assert await store.applications.list_by_job(job.id) == []


@pytest.mark.asyncio
async def test_seeker_withdraws_application() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    app = (await store.applications.list_by_job(job_id))[0]

    update = FakeUpdate(7)
    await withdraw(update, FakeContext(store, [app.id]))  # type: ignore[arg-type]

    loaded = await store.applications.get(app.id)
    assert loaded is not None
    assert loaded.status.value == "withdrawn"


@pytest.mark.asyncio
async def test_seeker_cannot_withdraw_others_application() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    app = (await store.applications.list_by_job(job_id))[0]
    await register_seeker(store, 8)

    update = FakeUpdate(8)
    await withdraw(update, FakeContext(store, [app.id]))  # type: ignore[arg-type]

    loaded = await store.applications.get(app.id)
    assert loaded is not None
    assert loaded.status.value == "submitted"
    assert "not found" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_my_applications_lists_seekers_apps() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]

    update = FakeUpdate(7)
    await my_applications(update, FakeContext(store))  # type: ignore[arg-type]

    assert "Engineer" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_employer_reviews_application_through_states() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    app = (await store.applications.list_by_job(job_id))[0]

    await review(FakeUpdate(1), FakeContext(store, [app.id]))  # type: ignore[arg-type]
    reviewed = await store.applications.get(app.id)
    assert reviewed is not None
    assert reviewed.status.value == "under_review"

    await shortlist(FakeUpdate(1), FakeContext(store, [app.id]))  # type: ignore[arg-type]
    shortlisted_app = await store.applications.get(app.id)
    assert shortlisted_app is not None
    assert shortlisted_app.status.value == "shortlisted"

    await accept(FakeUpdate(1), FakeContext(store, [app.id]))  # type: ignore[arg-type]
    accepted_app = await store.applications.get(app.id)
    assert accepted_app is not None
    assert accepted_app.status.value == "accepted"


@pytest.mark.asyncio
async def test_employer_rejects_application() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    app = (await store.applications.list_by_job(job_id))[0]

    await review(FakeUpdate(1), FakeContext(store, [app.id]))  # type: ignore[arg-type]

    update = FakeUpdate(1)
    await reject(update, FakeContext(store, [app.id]))  # type: ignore[arg-type]

    loaded = await store.applications.get(app.id)
    assert loaded is not None
    assert loaded.status.value == "rejected"


@pytest.mark.asyncio
async def test_employer_of_other_company_cannot_review() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]
    app = (await store.applications.list_by_job(job_id))[0]

    await register_employer(store, 2)
    await company(FakeUpdate(2), FakeContext(store, ["Globex"]))  # type: ignore[arg-type]

    update = FakeUpdate(2)
    await review(update, FakeContext(store, [app.id]))  # type: ignore[arg-type]

    loaded = await store.applications.get(app.id)
    assert loaded is not None
    assert loaded.status.value == "submitted"
    assert "not for a job in your company" in update.effective_chat.messages[-1]


@pytest.mark.asyncio
async def test_applications_lists_job_applications() -> None:
    store = make_store()
    job_id = await _publish_job(store, 1, "Engineer")
    await register_seeker(store, 7)
    await apply(FakeUpdate(7), FakeContext(store, [job_id]))  # type: ignore[arg-type]

    update = FakeUpdate(1)
    await applications(update, FakeContext(store, [job_id]))  # type: ignore[arg-type]

    assert "Engineer" in update.effective_chat.messages[-1]
    assert "seeker `7`" in update.effective_chat.messages[-1]
