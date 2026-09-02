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
  description = "IDs of private subnets for the DB subnet group."
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID of the ECS instances (allowed to connect to RDS)."
  type        = string
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GiB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Name of the default database."
  type        = string
  default     = "talent_hive"
}

variable "db_username" {
  description = "Master username for the RDS instance."
  type        = string
  default     = "talent"
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy (true for dev)."
  type        = bool
  default     = true
}
