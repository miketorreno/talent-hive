# Talent Hive Infrastructure (Terraform)

Terraform managing the AWS stack for Talent Hive: **ECS on EC2**, **RDS PostgreSQL**,
**Redis** (ElastiCache), and **S3** for artifact files. The `bot` and `worker` deploy
as two separate ECS services. `terraform apply` provisions the stack and deploys the
running bot/worker skeleton.

## Layout

```
infra/
├── main.tf                 # Root wiring of all modules
├── variables.tf            # Root-level inputs
├── outputs.tf              # Useful outputs (endpoints, service names)
├── versions.tf             # Provider + required_version constraints
├── terraform.tfvars.example# Copy to terraform.tfvars and fill in
└── modules/
    ├── networking/         # VPC, public/private subnets, NAT, routing
    ├── ecs/                # ECS cluster, ASG, task defs, services, IAM, secrets
    ├── rds/                # PostgreSQL instance + subnet group + security group
    ├── redis/              # ElastiCache replication group
    ├── s3/                 # Artifacts bucket (private, encrypted, versioned)
    └── ecr/                # Bot + worker ECR image repositories
```

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars   # fill in images + secrets
terraform init
terraform plan
terraform apply
```

Docker images for the bot and worker services are pushed to the ECR repositories
this stack provisions (`infra/modules/ecr`). If `bot_image` / `worker_image` are
left empty they default to the ECR repo `:latest` tags. Build the images from
`packages/bot/Dockerfile` and `packages/worker/Dockerfile` and push them to ECR
before (or as part of) applying — the CI/CD pipeline in `.github/workflows/deploy.yml`
does this automatically on merge to `main`.

Secrets (Telegram token, database URL, Groq/Google keys) are stored in AWS Secrets
Manager and injected into the ECS task definitions via `valueFrom`.

## Services

| Service  | Image        | Entry                      |
|----------|--------------|----------------------------|
| bot      | bot_image    | `python -m bot.main`       |
| worker   | worker_image | `arq worker.main.WorkerSettings` |

## Notes

- **Persistence**: the app store is currently Redis-backed. RDS and S3 are
  provisioned and reachable from ECS (security groups + `TH_S3_BUCKET` /
  `TH_DATABASE_URL` are wired to the tasks), but the application code does not yet
  read from PostgreSQL or S3. That socket for app-side integration is in place.
