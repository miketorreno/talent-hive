from __future__ import annotations

import json
from datetime import datetime

import asyncpg
from domain.application import Application, ApplicationStatus
from domain.artifact import Artifact, ArtifactOrigin, ArtifactType
from domain.company import Company, raise_one_company_per_owner_when
from domain.identities import Role, User
from domain.job import Job, JobStatus, search_terms
from domain.profile import SeekerProfile

from shared.store.applications import ApplicationRepository
from shared.store.artifacts import ArtifactRepository
from shared.store.companies import CompanyRepository
from shared.store.jobs import JobRepository
from shared.store.profiles import SeekerProfileRepository
from shared.store.users import UserRepository

from .schema import apply_schema


class PostgresStore:
    """Aggregate of Postgres-backed repositories sharing one connection.

    A thin container mirroring ``shared.store.Store``: the bot talks to a
    ``Store`` of repositories; this builds that store from a single asyncpg
    connection and ensures the schema exists.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn
        self.users: UserRepository = PostgresUserRepository(conn)
        self.companies: CompanyRepository = PostgresCompanyRepository(conn)
        self.jobs: JobRepository = PostgresJobRepository(conn)
        self.profiles: SeekerProfileRepository = PostgresSeekerProfileRepository(conn)
        self.applications: ApplicationRepository = PostgresApplicationRepository(conn)
        self.artifacts: ArtifactRepository = PostgresArtifactRepository(conn)

    async def migrate(self) -> None:
        await apply_schema(self.conn)


def _row_to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"expected datetime, got {type(value).__name__}")


async def _ensure_user(conn: asyncpg.Connection, user_id: int | None) -> None:
    """Ensure a Telegram user row exists so FK references can be satisfied.

    A User is the sole identity keyed by Telegram ID and is created lazily
    whenever someone interacts with the system; dependent rows (company
    members, applications, artifacts, profiles) reference it.
    """
    if user_id is None:
        return
    await conn.execute(
        "INSERT INTO users (telegram_id) VALUES ($1) ON CONFLICT (telegram_id) DO NOTHING",
        user_id,
    )


class PostgresUserRepository(UserRepository):
    """Postgres-backed user repository: one row per user, one per role."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, telegram_id: int) -> User | None:
        row = await self._conn.fetchrow(
            "SELECT telegram_id FROM users WHERE telegram_id = $1", telegram_id
        )
        if row is None:
            return None
        role_rows = await self._conn.fetch(
            "SELECT role FROM user_roles WHERE telegram_id = $1", telegram_id
        )
        roles = frozenset(Role(r["role"]) for r in role_rows)
        return User(telegram_id=telegram_id, roles=roles)

    async def save(self, user: User) -> None:
        await self._conn.execute(
            """
            INSERT INTO users (telegram_id) VALUES ($1)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            user.telegram_id,
        )
        await self._conn.execute(
            "DELETE FROM user_roles WHERE telegram_id = $1", user.telegram_id
        )
        if user.roles:
            await self._conn.executemany(
                """
                INSERT INTO user_roles (telegram_id, role) VALUES ($1, $2)
                """,
                [(user.telegram_id, role.value) for role in user.roles],
            )


class PostgresCompanyRepository(CompanyRepository):
    """Postgres-backed company repository.

    Enforces the one-company-per-owner rule at the persistence seam (ADR 0002),
    mirroring the Redis implementation, in addition to the UNIQUE(owner_id)
    constraint in the schema.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, company_id: str) -> Company | None:
        row = await self._conn.fetchrow(
            "SELECT id, name, description, owner_id FROM companies WHERE id = $1",
            company_id,
        )
        if row is None:
            return None
        return await self._build_company(row)

    async def find_by_owner(self, owner_id: int) -> Company | None:
        row = await self._conn.fetchrow(
            "SELECT id, name, description, owner_id FROM companies WHERE owner_id = $1",
            owner_id,
        )
        if row is None:
            return None
        return await self._build_company(row)

    async def find_by_member(self, user_id: int) -> Company | None:
        row = await self._conn.fetchrow(
            """
            SELECT c.id, c.name, c.description, c.owner_id
            FROM companies c
            WHERE c.owner_id = $1
               OR EXISTS (
                   SELECT 1 FROM company_recruiters cr
                   WHERE cr.company_id = c.id AND cr.recruiter_id = $1
               )
            """,
            user_id,
        )
        if row is None:
            return None
        return await self._build_company(row)

    async def save(self, company: Company) -> None:
        if company.owner_id is not None:
            await self._enforce_one_company_per_owner(company)
        async with self._conn.transaction():
            await _ensure_user(self._conn, company.owner_id)
            for recruiter_id in company.recruiter_ids:
                await _ensure_user(self._conn, recruiter_id)
            await self._conn.execute(
                """
                INSERT INTO companies (id, name, description, owner_id)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    owner_id = EXCLUDED.owner_id
                """,
                company.id,
                company.name,
                company.description,
                company.owner_id,
            )
            await self._conn.execute(
                "DELETE FROM company_recruiters WHERE company_id = $1", company.id
            )
            if company.recruiter_ids:
                await self._conn.executemany(
                    """
                    INSERT INTO company_recruiters (company_id, recruiter_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    [(company.id, recruiter_id) for recruiter_id in company.recruiter_ids],
                )

    async def delete(self, company_id: str) -> None:
        async with self._conn.transaction():
            await self._conn.execute(
                "DELETE FROM company_recruiters WHERE company_id = $1", company_id
            )
            await self._conn.execute(
                "DELETE FROM companies WHERE id = $1", company_id
            )

    async def _build_company(self, row: asyncpg.Record) -> Company:
        recruiter_rows = await self._conn.fetch(
            "SELECT recruiter_id FROM company_recruiters WHERE company_id = $1",
            row["id"],
        )
        company = Company(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            owner_id=row["owner_id"],
            recruiter_ids={r["recruiter_id"] for r in recruiter_rows},
        )
        return company

    async def _enforce_one_company_per_owner(self, company: Company) -> None:
        existing_id = await self._conn.fetchval(
            "SELECT id FROM companies WHERE owner_id = $1",
            company.owner_id,
        )
        raise_one_company_per_owner_when(
            existing_id is not None and existing_id != company.id
        )


class PostgresJobRepository(JobRepository):
    """Postgres-backed job repository."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, job_id: str) -> Job | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM jobs WHERE id = $1", job_id
        )
        if row is None:
            return None
        return _decode_job_row(row)

    async def list_by_company(self, company_id: str) -> list[Job]:
        rows = await self._conn.fetch(
            "SELECT * FROM jobs WHERE company_id = $1 ORDER BY created_at",
            company_id,
        )
        return [_decode_job_row(row) for row in rows]

    async def list_published(self) -> list[Job]:
        rows = await self._conn.fetch(
            "SELECT * FROM jobs WHERE status = 'published' ORDER BY created_at"
        )
        return [_decode_job_row(row) for row in rows]

    async def search_published(self, query: str) -> list[Job]:
        terms = search_terms(query)
        if not terms:
            return []
        conditions = " AND ".join(
            "(title ILIKE $%d OR description ILIKE $%d OR requirements ILIKE $%d)"
            % (i, i, i)
            for i in range(1, len(terms) + 1)
        )
        params = [f"%{_escape_like(term)}%" for term in terms]
        sql = (
            "SELECT * FROM jobs WHERE status = 'published' AND "
            f"({conditions}) ORDER BY created_at"
        )
        rows = await self._conn.fetch(sql, *params)
        return [_decode_job_row(row) for row in rows]

    async def save(self, job: Job) -> None:
        await self._conn.execute(
            """
            INSERT INTO jobs
                (id, company_id, title, description, requirements,
                 created_by, status, created_at, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                company_id = EXCLUDED.company_id,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                requirements = EXCLUDED.requirements,
                created_by = EXCLUDED.created_by,
                status = EXCLUDED.status,
                created_at = EXCLUDED.created_at,
                expires_at = EXCLUDED.expires_at
            """,
            job.id,
            job.company_id,
            job.title,
            job.description,
            job.requirements,
            job.created_by,
            job.status.value,
            job.created_at,
            job.expires_at,
        )

    async def delete(self, job_id: str) -> None:
        await self._conn.execute("DELETE FROM jobs WHERE id = $1", job_id)


class PostgresSeekerProfileRepository(SeekerProfileRepository):
    """Postgres-backed seeker profile repository (one row per seeker)."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, seeker_id: int) -> SeekerProfile | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM seeker_profiles WHERE seeker_id = $1", seeker_id
        )
        if row is None:
            return None
        return SeekerProfile(
            seeker_id=row["seeker_id"],
            skills=json.loads(row["skills"]),
            experience=json.loads(row["experience"]),
            background=row["background"],
            updated_at=_row_to_datetime(row["updated_at"]),
        )

    async def save(self, profile: SeekerProfile) -> None:
        await _ensure_user(self._conn, profile.seeker_id)
        await self._conn.execute(
            """
            INSERT INTO seeker_profiles
                (seeker_id, skills, experience, background, updated_at)
            VALUES ($1, $2::jsonb, $3::jsonb, $4, $5)
            ON CONFLICT (seeker_id) DO UPDATE SET
                skills = EXCLUDED.skills,
                experience = EXCLUDED.experience,
                background = EXCLUDED.background,
                updated_at = EXCLUDED.updated_at
            """,
            profile.seeker_id,
            json.dumps(profile.skills),
            json.dumps(profile.experience),
            profile.background,
            profile.updated_at,
        )


class PostgresApplicationRepository(ApplicationRepository):
    """Postgres-backed application repository."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, application_id: str) -> Application | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM applications WHERE id = $1", application_id
        )
        if row is None:
            return None
        return _decode_application_row(row)

    async def list_by_job(self, job_id: str) -> list[Application]:
        rows = await self._conn.fetch(
            "SELECT * FROM applications WHERE job_id = $1 ORDER BY created_at",
            job_id,
        )
        return [_decode_application_row(row) for row in rows]

    async def list_by_seeker(self, seeker_id: int) -> list[Application]:
        rows = await self._conn.fetch(
            "SELECT * FROM applications WHERE seeker_id = $1 ORDER BY created_at",
            seeker_id,
        )
        return [_decode_application_row(row) for row in rows]

    async def save(self, application: Application) -> None:
        await _ensure_user(self._conn, application.seeker_id)
        await self._conn.execute(
            """
            INSERT INTO applications (id, job_id, seeker_id, status, cover_letter, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                cover_letter = EXCLUDED.cover_letter,
                created_at = EXCLUDED.created_at
            """,
            application.id,
            application.job_id,
            application.seeker_id,
            application.status.value,
            application.cover_letter,
            application.created_at,
        )


class PostgresArtifactRepository(ArtifactRepository):
    """Postgres-backed artifact repository."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def get(self, artifact_id: str) -> Artifact | None:
        row = await self._conn.fetchrow(
            "SELECT * FROM artifacts WHERE id = $1", artifact_id
        )
        if row is None:
            return None
        return _decode_artifact_row(row)

    async def list_by_owner(
        self, owner_id: int, type: ArtifactType | None = None
    ) -> list[Artifact]:
        if type is None:
            rows = await self._conn.fetch(
                "SELECT * FROM artifacts WHERE owner_id = $1 ORDER BY created_at",
                owner_id,
            )
        else:
            rows = await self._conn.fetch(
                """
                SELECT * FROM artifacts
                WHERE owner_id = $1 AND type = $2 ORDER BY created_at
                """,
                owner_id,
                type.value,
            )
        return [_decode_artifact_row(row) for row in rows]

    async def save(self, artifact: Artifact) -> None:
        await _ensure_user(self._conn, artifact.owner_id)
        await self._conn.execute(
            """
            INSERT INTO artifacts (id, type, owner_id, origin, text, storage_key, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                owner_id = EXCLUDED.owner_id,
                origin = EXCLUDED.origin,
                text = EXCLUDED.text,
                storage_key = EXCLUDED.storage_key,
                created_at = EXCLUDED.created_at
            """,
            artifact.id,
            artifact.type.value,
            artifact.owner_id,
            artifact.origin.value,
            artifact.text,
            artifact.storage_key,
            artifact.created_at,
        )


def _escape_like(term: str) -> str:
    """Escape LIKE wildcards so a search term matches literally (ILIKE parity).

    Postgres default LIKE escape character is the backslash; without escaping a
    user-supplied '%' or '_' would act as a wildcard, unlike the Redis backend's
    literal substring match. A literal backslash is doubled so it survives as-is.
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _decode_job_row(row: asyncpg.Record) -> Job:
    return Job(
        id=row["id"],
        company_id=row["company_id"],
        title=row["title"],
        description=row["description"],
        requirements=row["requirements"],
        created_by=row["created_by"],
        status=JobStatus(row["status"]),
        created_at=_row_to_datetime(row["created_at"]),
        expires_at=_row_to_datetime(row["expires_at"]) if row["expires_at"] else None,
    )


def _decode_application_row(row: asyncpg.Record) -> Application:
    return Application(
        id=row["id"],
        job_id=row["job_id"],
        seeker_id=row["seeker_id"],
        status=ApplicationStatus(row["status"]),
        cover_letter=row["cover_letter"],
        created_at=_row_to_datetime(row["created_at"]),
    )


def _decode_artifact_row(row: asyncpg.Record) -> Artifact:
    return Artifact(
        id=row["id"],
        type=ArtifactType(row["type"]),
        owner_id=row["owner_id"],
        origin=ArtifactOrigin(row["origin"]),
        text=row["text"],
        storage_key=row["storage_key"],
        created_at=_row_to_datetime(row["created_at"]),
    )
