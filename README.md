# Talent Hive

An AI-powered Telegram job board that connects employers and job seekers via a
Telegram bot. Uses AI (through a provider-agnostic abstraction) to automate
generation of cover letters, resumes, and job descriptions.

## Monorepo layout

- `packages/domain/` — pure entities + state machines (the single behavioral test seam)
- `packages/shared/` — common config/types and persistence shells
- `packages/ai/` — provider-agnostic LLM abstraction
- `packages/bot/` — Telegram gateway (long polling)
- `packages/worker/` — `arq` worker consuming AI generation jobs
- `infra/` — Terraform-managed AWS infrastructure

## Development

Install [Poetry](https://python-poetry.org) and [Nox](https://nox.thea.codes):

```sh
pip install poetry nox
```

Run all tasks (test, lint, typecheck):

```sh
nox
```

Run a single task:

```sh
nox -s test
nox -s lint
nox -s typecheck
```

Run the bot:

```sh
set -a; source .env; set +a   # TH_TELEGRAM_TOKEN, TH_REDIS_URL
cd packages/bot && poetry install && poetry run talent-hive-bot
```

See `CONTEXT.md` for the domain vocabulary used across the codebase.
