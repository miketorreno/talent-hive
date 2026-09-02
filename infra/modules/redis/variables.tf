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
  description = "IDs of private subnets for the ElastiCache subnet group."
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID of the ECS instances (allowed to connect to Redis)."
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t3.micro"
}
