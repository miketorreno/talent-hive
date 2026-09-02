# Talent Hive

An AI-powered Telegram job board that connects employers and job seekers via a Telegram bot. Uses AI (through a provider-agnostic abstraction) to automate the generation of cover letters, resumes, and job descriptions.

## Language

**Company**:
An organization that offers jobs. Owned by an owner or represented by recruiters.
_Avoid_: Organization, business

**Employer**:
A person who represents a company as either its owner or a recruiter, and publishes jobs on its behalf.
_Avoid_: Recruiter (as a standalone concept), company

**Job Seeker**:
A person who applies to jobs.
_Avoid_: Candidate, applicant

**Job**:
A vacancy created by an employer for a company, with a title, description, requirements, and status (`draft`, `published`, `expired`, `closed`, `archived`).
_Avoid_: Vacancy, job posting, position

**Application**:
A job seeker's submission to a specific job, tracking that seeker's progress through review (`submitted`, `under_review`, `shortlisted`, `accepted`, `rejected`, `withdrawn`).
_Avoid_: Submission, applicant

**Owner**:
A company's creator, who manages the company and its recruiters.
_Avoid_: Admin, founder

**Recruiter**:
A person added by an owner to publish jobs for a company.
_Avoid_: Hiring manager (as a role)

**Artifact**:
A document that is either AI-generated, user-written, or user-uploaded. Covers cover letters, resumes, and job descriptions.
_Avoid_: Document, file

**Seeker Profile**:
The job seeker's stored skills, experience, and background, used as the template base for generating artifacts.

## AI Artifact Origins

- **ai_generated**: produced by an LLM provider
- **user_written**: typed by the user in chat
- **user_uploaded**: a file the user provided

