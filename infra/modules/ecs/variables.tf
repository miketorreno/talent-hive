variable "project" {
  description = "Project name prefix for resource naming."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC."
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs of private subnets for ECS instances."
  type        = list(string)
}

variable "bot_image" {
  description = "Docker image URI for the bot service."
  type        = string
}

variable "worker_image" {
  description = "Docker image URI for the worker service."
  type        = string
}

variable "bot_desired_count" {
  description = "Desired count of bot tasks."
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Desired count of worker tasks."
  type        = number
  default     = 1
}

variable "instance_type" {
  description = "EC2 instance type for the ECS cluster."
  type        = string
  default     = "t3.small"
}

variable "redis_url" {
  description = "Redis connection URL for the tasks."
  type        = string
  sensitive   = true
}

variable "database_url" {
  description = "PostgreSQL connection URL for the tasks."
  type        = string
  sensitive   = true
}

variable "telegram_token" {
  description = "Telegram bot token."
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key (empty string to disable)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_ai_api_key" {
  description = "Google AI API key (empty string to disable)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "rds_security_group_id" {
  description = "Security group ID of the RDS instance."
  type        = string
}

variable "redis_security_group_id" {
  description = "Security group ID of the Redis cluster."
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 artifacts bucket."
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 artifacts bucket."
  type        = string
}
