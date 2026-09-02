# --- Networking -------------------------------------------------------------

module "networking" {
  source = "./modules/networking"

  project     = var.project
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# --- RDS PostgreSQL ---------------------------------------------------------

module "rds" {
  source = "./modules/rds"

  project               = var.project
  environment           = var.environment
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.ecs.security_group_id
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
}

# --- Redis (ElastiCache) ----------------------------------------------------

module "redis" {
  source = "./modules/redis"

  project               = var.project
  environment           = var.environment
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.ecs.security_group_id
  node_type             = var.redis_node_type
}

# --- S3 Artifacts Bucket ----------------------------------------------------

module "s3" {
  source = "./modules/s3"

  project     = var.project
  environment = var.environment
}

# --- ECS on EC2 (bot + worker) ----------------------------------------------

module "ecs" {
  source = "./modules/ecs"

  project                 = var.project
  environment             = var.environment
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  bot_image               = var.bot_image
  worker_image            = var.worker_image
  instance_type           = var.ecs_instance_type
  bot_desired_count       = var.bot_desired_count
  worker_desired_count    = var.worker_desired_count
  redis_url               = module.redis.redis_url
  database_url            = module.rds.database_url
  telegram_token          = var.telegram_token
  groq_api_key            = var.groq_api_key
  google_ai_api_key       = var.google_ai_api_key
  rds_security_group_id   = module.rds.security_group_id
  redis_security_group_id = module.redis.security_group_id
  s3_bucket_arn           = module.s3.bucket_arn
  s3_bucket_name          = module.s3.bucket_id
}
