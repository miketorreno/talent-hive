output "endpoint" {
  description = "RDS endpoint address."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "RDS port."
  value       = aws_db_instance.this.port
}

output "database_url" {
  description = "PostgreSQL connection URL."
  value       = "postgresql://${var.db_username}:${random_password.db.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}"
  sensitive   = true
}

output "security_group_id" {
  description = "ID of the RDS security group."
  value       = aws_security_group.this.id
}

output "password_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the DB password."
  value       = aws_secretsmanager_secret.db_password.arn
}
