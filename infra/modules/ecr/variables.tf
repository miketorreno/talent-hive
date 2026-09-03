variable "project" {
  description = "Project name prefix for resource naming."
  type        = string
}

variable "force_delete" {
  description = "Force deletion of the ECR repositories on destroy even if they contain images."
  type        = bool
  default     = false
}
