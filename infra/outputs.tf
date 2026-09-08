output "vpc_id" {
  description = "ID of the VPC."
  value       = module.networking.vpc_id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs.cluster_name
}

output "bot_service_name" {
  description = "Name of the bot ECS service."
  value       = module.ecs.bot_service_name
}

output "worker_service_name" {
  description = "Name of the worker ECS service."
  value       = module.ecs.worker_service_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint."
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint."
  value       = module.redis.endpoint
}

output "s3_bucket_id" {
  description = "ID of the artifacts S3 bucket."
  value       = module.s3.bucket_id
}

output "database_url_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the database URL."
  value       = module.rds.password_secret_arn
}

output "bot_repository_url" {
  description = "URL of the bot ECR repository."
  value       = module.ecr.bot_repository_url
}

output "worker_repository_url" {
  description = "URL of the worker ECR repository."
  value       = module.ecr.worker_repository_url
}
