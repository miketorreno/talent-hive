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

## CI/CD

- **CI** (`.github/workflows/ci.yml`): lint + test + typecheck on every PR and push to `main`.
- **CD** (`.github/workflows/deploy.yml`): on a green `main` run, builds the bot + worker
  images, pushes them to ECR, and runs `terraform apply` to deploy to ECS.
- **First-time AWS setup** (HITL): run `scripts/setup-aws-cicd.sh` to create the CI IAM
  user, wire AWS credentials and app secrets as GitHub secrets/variables, create the Terraform
  remote state backend, and validate. See `infra/README.md` for the deployment layout.
