output "cluster_id" {
  description = "ID of the ECS cluster."
  value       = aws_ecs_cluster.this.id
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "security_group_id" {
  description = "ID of the ECS instances security group."
  value       = aws_security_group.ecs.id
}

output "task_execution_role_arn" {
  description = "ARN of the ECS task execution role."
  value       = aws_iam_role.ecs_task_execution.arn
}

output "bot_service_name" {
  description = "Name of the bot ECS service."
  value       = aws_ecs_service.bot.name
}

output "worker_service_name" {
  description = "Name of the worker ECS service."
  value       = aws_ecs_service.worker.name
}
