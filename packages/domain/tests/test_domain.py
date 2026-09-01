import pytest
from domain.application import Application, ApplicationError, ApplicationStatus
from domain.artifact import Artifact, ArtifactError, ArtifactOrigin, ArtifactType
from domain.company import Company, CompanyError, CompanyRegistry, EmployerRole
from domain.identities import Role, RoleError, User
from domain.job import Job, JobError, JobStatus
from domain.profile import ProfileError, SeekerProfile


class TestRoleTransition:
    def test_user_can_hold_both_roles(self):
        user = User(telegram_id=1)
        with_both = user.add_role(Role.EMPLOYER).add_role(Role.JOB_SEEKER)
        assert with_both.is_employer and with_both.is_job_seeker

    def test_add_role_is_immutable(self):
        user = User(telegram_id=1)
        changed = user.add_role(Role.JOB_SEEKER)
        assert not user.is_job_seeker
        assert changed.is_job_seeker

    def test_unknown_role_is_rejected(self):
        user = User(telegram_id=1)
        with pytest.raises(RoleError):
            user.add_role("superuser")  # type: ignore[arg-type]


class TestJobStateMachine:
    def _new_job(self, complete=True) -> Job:
        job = Job(
            id="j1",
            company_id="c1",
            title="Engineer",
            description="Build things",
            requirements="Python" if complete else "",
        )
        return job

    def test_draft_to_published(self):
        job = self._new_job()
        job.publish()
        assert job.status == JobStatus.PUBLISHED

    def test_draft_to_closed(self):
        job = self._new_job()
        job.close()
        assert job.status == JobStatus.CLOSED

    def test_published_to_expired(self):
        job = self._new_job()
        job.publish()
        job.expire()
        assert job.status == JobStatus.EXPIRED

    def test_expired_to_published_reopen(self):
        job = self._new_job()
        job.publish()
        job.expire()
        job.publish()
        assert job.status == JobStatus.PUBLISHED

    def test_published_to_closed(self):
        job = self._new_job()
        job.publish()
        job.close()
        assert job.status == JobStatus.CLOSED

    def test_closed_to_archived(self):
        job = self._new_job()
        job.publish()
        job.close()
        job.archive()
        assert job.status == JobStatus.ARCHIVED

    def test_cannot_archive_a_draft(self):
        job = self._new_job()
        with pytest.raises(JobError):
            job.archive()

    def test_cannot_publish_incomplete_job(self):
        job = self._new_job(complete=False)
        with pytest.raises(JobError):
            job.publish()
        assert job.status == JobStatus.DRAFT

    def test_cannot_transition_terminal_archived(self):
        job = self._new_job()
        job.publish()
        job.close()
        job.archive()
        with pytest.raises(JobError):
            job.transition(JobStatus.PUBLISHED)

    def test_published_job_is_active(self):
        job = self._new_job()
        assert not job.is_active
        job.publish()
        assert job.is_active


class TestApplicationStateMachine:
    def _new_app(self) -> Application:
        return Application(id="a1", job_id="j1", seeker_id=7)

    def test_full_accept_path(self):
        app = self._new_app()
        app.start_review()
        app.shortlist()
        app.accept()
        assert app.status == ApplicationStatus.ACCEPTED

    def test_full_reject_path(self):
        app = self._new_app()
        app.start_review()
        app.shortlist()
        app.reject()
        assert app.status == ApplicationStatus.REJECTED

    def test_reject_under_review(self):
        app = self._new_app()
        app.start_review()
        app.reject()
        assert app.status == ApplicationStatus.REJECTED

    def test_withdraw_from_submitted(self):
        app = self._new_app()
        app.withdraw()
        assert app.status == ApplicationStatus.WITHDRAWN

    def test_cannot_shortlist_before_review(self):
        app = self._new_app()
        with pytest.raises(ApplicationError):
            app.shortlist()

    def test_cannot_accept_before_shortlist(self):
        app = self._new_app()
        app.start_review()
        with pytest.raises(ApplicationError):
            app.accept()

    def test_terminal_accepted_is_inactive(self):
        app = self._new_app()
        app.start_review()
        app.shortlist()
        app.accept()
        assert not app.is_active

    def test_submitted_is_active(self):
        app = self._new_app()
        assert app.is_active

    def test_withdraw_from_under_review(self):
        app = self._new_app()
        app.start_review()
        app.withdraw()
        assert app.status == ApplicationStatus.WITHDRAWN

    def test_withdraw_from_shortlisted(self):
        app = self._new_app()
        app.start_review()
        app.shortlist()
        app.withdraw()
        assert app.status == ApplicationStatus.WITHDRAWN

    def test_cannot_further_transition_withdrawn(self):
        app = self._new_app()
        app.withdraw()
        with pytest.raises(ApplicationError):
            app.start_review()


class TestArtifact:
    def test_ai_generated_needs_text(self):
        with pytest.raises(ArtifactError):
            Artifact(ArtifactType.COVER_LETTER, 1, ArtifactOrigin.AI_GENERATED)

    def test_user_uploaded_needs_storage_key(self):
        with pytest.raises(ArtifactError):
            Artifact(ArtifactType.RESUME, 1, ArtifactOrigin.USER_UPLOADED)

    def test_user_written_needs_text(self):
        with pytest.raises(ArtifactError):
            Artifact(ArtifactType.RESUME, 1, ArtifactOrigin.USER_WRITTEN)

    def test_uploaded_artifact_accepts_key(self):
        a = Artifact(ArtifactType.RESUME, 1, ArtifactOrigin.USER_UPLOADED, storage_key="s3://x")
        assert a.storage_key == "s3://x"

    def test_storage_key_forbidden_for_written(self):
        with pytest.raises(ArtifactError):
            Artifact(
                ArtifactType.JOB_DESCRIPTION,
                1,
                ArtifactOrigin.USER_WRITTEN,
                text="t",
                storage_key="k",
            )

    def test_written_artifact_ok(self):
        a = Artifact(ArtifactType.JOB_DESCRIPTION, 1, ArtifactOrigin.USER_WRITTEN, text="hello")
        assert a.text == "hello"

    def test_invalid_type_rejected(self):
        with pytest.raises(ArtifactError):
            Artifact("nonsense", 1, ArtifactOrigin.AI_GENERATED, text="t")  # type: ignore[arg-type]


class TestCompany:
    def test_requires_name(self):
        with pytest.raises(CompanyError):
            Company(id="c1", name="")

    def test_set_owner(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        assert c.owner_id == 7

    def test_owner_cannot_change(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        with pytest.raises(CompanyError):
            c.set_owner(8)

    def test_add_recruiter(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        c.add_recruiter(9)
        assert c.member_role(9) == EmployerRole.RECRUITER

    def test_owner_not_duplicated_as_recruiter(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        c.add_recruiter(7)
        assert c.member_role(7) == EmployerRole.OWNER
        assert 7 not in c.recruiter_ids

    def test_members(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        c.add_recruiter(9)
        assert c.members() == {7, 9}

    def test_is_member(self):
        c = Company(id="c1", name="Acme")
        c.set_owner(7)
        assert c.is_member(7)
        assert not c.is_member(5)


class TestCompanyRegistry:
    def _company(self, company_id: str, owner_id: int | None) -> Company:
        return Company(id=company_id, name="Acme", owner_id=owner_id)

    def _get(self, registry: CompanyRegistry, company_id: str) -> Company:
        company = registry.get(company_id)
        assert company is not None
        return company

    def test_register_first_company(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=7))
        assert registry.get("c1") is not None

    def test_same_owner_cannot_start_second_company(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=7))
        with pytest.raises(CompanyError):
            registry.add_company(self._company("c2", owner_id=7))

    def test_distinct_owners_may_each_have_a_company(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=7))
        registry.add_company(self._company("c2", owner_id=8))
        assert registry.get("c1") and registry.get("c2")

    def test_duplicate_company_id_rejected(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=7))
        with pytest.raises(CompanyError):
            registry.add_company(self._company("c1", owner_id=8))

    def test_registering_unowned_company_is_allowed(self):
        registry = CompanyRegistry()
        company = self._company("c1", owner_id=None)
        registry.add_company(company)
        assert registry.get("c1") is company

    def test_set_owner_after_registration(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=None))
        registry.set_owner("c1", 7)
        assert self._get(registry, "c1").owner_id == 7

    def test_cannot_give_unowned_company_to_busy_owner(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=7))
        registry.add_company(self._company("c2", owner_id=None))
        with pytest.raises(CompanyError):
            registry.set_owner("c2", 7)

    def test_set_owner_unknown_company_rejected(self):
        registry = CompanyRegistry()
        with pytest.raises(CompanyError):
            registry.set_owner("nope", 7)

    def test_reset_owner_to_same_owner_is_idempotent(self):
        registry = CompanyRegistry()
        registry.add_company(self._company("c1", owner_id=None))
        registry.set_owner("c1", 7)
        registry.set_owner("c1", 7)
        assert self._get(registry, "c1").owner_id == 7

    def test_unknown_company_is_none(self):
        registry = CompanyRegistry()
        assert registry.get("nope") is None


class TestSeekerProfile:
    def test_incomplete_by_default(self):
        p = SeekerProfile(seeker_id=1)
        assert not p.is_complete

    def test_complete_when_skills_and_background(self):
        p = SeekerProfile(seeker_id=1)
        p.add_skill("Python")
        p.set_background("5 years backend")
        assert p.is_complete

    def test_blank_skill_rejected(self):
        p = SeekerProfile(seeker_id=1)
        with pytest.raises(ProfileError):
            p.add_skill("   ")

    def test_blank_background_rejected(self):
        p = SeekerProfile(seeker_id=1)
        with pytest.raises(ProfileError):
            p.set_background("  ")

    def test_experience_stored(self):
        p = SeekerProfile(seeker_id=1)
        p.add_experience("Built a bot")
        assert "Built a bot" in p.experience
