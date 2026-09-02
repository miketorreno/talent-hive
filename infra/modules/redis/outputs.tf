output "endpoint" {
  description = "Redis primary endpoint address."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  description = "Redis port."
  value       = aws_elasticache_replication_group.this.port
}

output "redis_url" {
  description = "Redis connection URL."
  value       = "redis://${aws_elasticache_replication_group.this.primary_endpoint_address}:${aws_elasticache_replication_group.this.port}/0"
}

output "security_group_id" {
  description = "ID of the Redis security group."
  value       = aws_security_group.this.id
}
