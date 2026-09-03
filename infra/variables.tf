variable "project" {
  description = "Project name prefix for all resources."
  type        = string
  default     = "talent-hive"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "eu-west-2"
}

# --- Networking -------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

# --- ECS --------------------------------------------------------------------

variable "bot_image" {
  description = "Docker image URI for the bot service. Leave empty to use the ECR repository tag :latest."
  type        = string
  default     = ""
}

variable "worker_image" {
  description = "Docker image URI for the worker service. Leave empty to use the ECR repository tag :latest."
  type        = string
  default     = ""
}

# --- ECR --------------------------------------------------------------------

variable "ecr_force_delete" {
  description = "Force deletion of ECR repositories on destroy even if they contain images."
  type        = bool
  default     = false
}

variable "ecs_instance_type" {
  description = "EC2 instance type for the ECS cluster."
  type        = string
  default     = "t3.small"
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

# --- RDS --------------------------------------------------------------------

variable "rds_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GiB."
  type        = number
  default     = 20
}

# --- Redis ------------------------------------------------------------------

variable "redis_node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t3.micro"
}

# --- Secrets (sensitive) ----------------------------------------------------

variable "telegram_token" {
  description = "Telegram bot token."
  type        = string
  sensitive   = true
}

variable "groq_api_key" {
  description = "Groq API key."
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_ai_api_key" {
  description = "Google AI API key."
  type        = string
  default     = ""
  sensitive   = true
}
