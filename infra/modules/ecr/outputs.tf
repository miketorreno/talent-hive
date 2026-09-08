output "bot_repository_url" {
  description = "URL of the bot ECR repository."
  value       = aws_ecr_repository.bot.repository_url
}

output "worker_repository_url" {
  description = "URL of the worker ECR repository."
  value       = aws_ecr_repository.worker.repository_url
}

output "bot_repository_name" {
  description = "Name of the bot ECR repository."
  value       = aws_ecr_repository.bot.name
}

output "worker_repository_name" {
  description = "Name of the worker ECR repository."
  value       = aws_ecr_repository.worker.name
}
