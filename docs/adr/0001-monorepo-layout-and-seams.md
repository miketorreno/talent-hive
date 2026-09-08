# Monorepo layout and seams

Talent Hive is a Poetry-workspace monorepo of five packages — `domain` (pure entities and state machines, no I/O), `shared` (config + thin persistence repositories), `ai` (provider-agnostic LLM seam), `bot` (Telegram gateway, long polling), and `worker` (arq job consumer) — plus `infra/` (Terraform), coordinated by `nox`. Dependencies flow one way: `domain ← shared ← {ai, bot} ← worker`; no package imports anything above itself.

The single behavioral test seam is `domain`: every rule worth asserting (job/application state machines, artifact origin/type, one-company-per-employer, seeker profile constraints) lives there, free of I/O. The bot, worker, AI providers, and repositories are thin I/O shells and are not behaviorally unit-tested; `ai` gets lightweight contract tests against a fake provider. `shared` deliberately co-locates `config` and `store` because bot, worker, and ai all need both and the store stays a thin adapter behind repository interfaces.
