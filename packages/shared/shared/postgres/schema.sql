-- Talent Hive Postgres data model.
--
-- Relational projection of the `domain` package entities (see docs/adr/0001).
-- Thin persistence shells map these rows to/from domain objects; every
-- behavioral invariant also lives in `domain`, the single test seam.
--
-- Idempotent: safe to run repeatedly (CREATE ... IF NOT EXISTS and guarded
-- enum creation). Enums are guarded so re-applying a migration over an
-- existing database does not error.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

-- CREATE TYPE has no IF NOT EXISTS, so each enum is guarded by a DO block.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role') THEN
        CREATE TYPE role AS ENUM ('employer', 'job_seeker');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'employer_role') THEN
        CREATE TYPE employer_role AS ENUM ('owner', 'recruiter');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'job_status') THEN
        CREATE TYPE job_status AS ENUM (
            'draft', 'published', 'expired', 'closed', 'archived'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status') THEN
        CREATE TYPE application_status AS ENUM (
            'submitted', 'under_review', 'shortlisted',
            'accepted', 'rejected', 'withdrawn'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_type') THEN
        CREATE TYPE artifact_type AS ENUM (
            'cover_letter', 'resume', 'job_description'
        );
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'artifact_origin') THEN
        CREATE TYPE artifact_origin AS ENUM (
            'ai_generated', 'user_written', 'user_uploaded'
        );
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Users and roles
-- ---------------------------------------------------------------------------

-- The sole identity in the system: a Telegram user ID.
CREATE TABLE IF NOT EXISTS users (
    telegram_id   bigint PRIMARY KEY,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- A user can hold both the EMPLOYER and JOB_SEEKER roles; the two are not
-- mutually exclusive, so roles live in a separate table.
CREATE TABLE IF NOT EXISTS user_roles (
    telegram_id   bigint NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    role          role NOT NULL,
    PRIMARY KEY (telegram_id, role)
);

-- ---------------------------------------------------------------------------
-- Companies and employer membership
-- ---------------------------------------------------------------------------

-- An organization that offers jobs. An employer holds at most one company, so
-- owner_id is UNIQUE (enforced at the persistence seam per ADR 0002, and
-- mirrored here by the unique index).
CREATE TABLE IF NOT EXISTS companies (
    id            text PRIMARY KEY,
    name          text NOT NULL,
    description   text NOT NULL DEFAULT '',
    owner_id      bigint UNIQUE REFERENCES users(telegram_id) ON DELETE SET NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- An owner may add Recruiters who publish jobs on the company's behalf.
CREATE TABLE IF NOT EXISTS company_recruiters (
    company_id    text NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    recruiter_id  bigint NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    PRIMARY KEY (company_id, recruiter_id)
);

-- ---------------------------------------------------------------------------
-- Jobs
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS jobs (
    id            text PRIMARY KEY,
    company_id    text NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title         text NOT NULL,
    description   text NOT NULL,
    requirements  text NOT NULL DEFAULT '',
    created_by    bigint REFERENCES users(telegram_id) ON DELETE SET NULL,
    status        job_status NOT NULL DEFAULT 'draft',
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz
);

CREATE INDEX IF NOT EXISTS jobs_by_company_idx ON jobs (company_id);
CREATE INDEX IF NOT EXISTS jobs_published_idx ON jobs (status) WHERE status = 'published';

-- ---------------------------------------------------------------------------
-- Seeker profiles
-- ---------------------------------------------------------------------------

-- One Seeker Profile per job seeker (PK on seeker_id).
-- skills/experience are JSON arrays; background is free text.
CREATE TABLE IF NOT EXISTS seeker_profiles (
    seeker_id     bigint PRIMARY KEY REFERENCES users(telegram_id) ON DELETE CASCADE,
    skills        jsonb NOT NULL DEFAULT '[]'::jsonb,
    experience    jsonb NOT NULL DEFAULT '[]'::jsonb,
    background    text NOT NULL DEFAULT '',
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Applications
-- ---------------------------------------------------------------------------

-- A job seeker's submission to a specific job. A seeker may apply to a given
-- job at most once; deduped via the UNIQUE (job_id, seeker_id) constraint.
CREATE TABLE IF NOT EXISTS applications (
    id            text PRIMARY KEY,
    job_id        text NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    seeker_id     bigint NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    status        application_status NOT NULL DEFAULT 'submitted',
    cover_letter  text NOT NULL DEFAULT '',
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (job_id, seeker_id)
);

CREATE INDEX IF NOT EXISTS applications_by_seeker_idx ON applications (seeker_id);

-- ---------------------------------------------------------------------------
-- Artifacts (generated-doc history: cover letters, resumes, job descriptions)
-- ---------------------------------------------------------------------------

-- A generated document tagged by type and origin. Text is stored inline
-- (ai_generated / user_written); user_uploaded artifacts carry an S3
-- storage key instead.
CREATE TABLE IF NOT EXISTS artifacts (
    id            text PRIMARY KEY,
    type          artifact_type NOT NULL,
    owner_id      bigint NOT NULL REFERENCES users(telegram_id) ON DELETE CASCADE,
    origin        artifact_origin NOT NULL,
    text          text NOT NULL DEFAULT '',
    storage_key   text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS artifacts_by_owner_idx ON artifacts (owner_id);

-- One resume per user: a partial unique index over the resume rows only, so a
-- user can hold many artifacts but never more than one RESUME.
CREATE UNIQUE INDEX IF NOT EXISTS one_resume_per_owner_idx
    ON artifacts (owner_id) WHERE type = 'resume';
