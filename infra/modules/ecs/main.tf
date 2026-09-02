data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# --- Security Group ---------------------------------------------------------

resource "aws_security_group" "ecs" {
  name_prefix = "${var.project}-${var.environment}-ecs-"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project}-${var.environment}-ecs"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "ecs_to_rds" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id
  security_group_id        = var.rds_security_group_id
}

resource "aws_security_group_rule" "ecs_to_redis" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id
  security_group_id        = var.redis_security_group_id
}

# --- Secrets Manager --------------------------------------------------------

resource "aws_secretsmanager_secret" "telegram_token" {
  name = "${var.project}/${var.environment}/telegram-token"

  tags = {
    Name = "${var.project}-${var.environment}-telegram-token"
  }
}

resource "aws_secretsmanager_secret_version" "telegram_token" {
  secret_id     = aws_secretsmanager_secret.telegram_token.id
  secret_string = jsonencode({ telegram_token = var.telegram_token })
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "${var.project}/${var.environment}/database-url"

  tags = {
    Name = "${var.project}-${var.environment}-database-url"
  }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id     = aws_secretsmanager_secret.database_url.id
  secret_string = jsonencode({ database_url = var.database_url })
}

resource "aws_secretsmanager_secret" "groq_api_key" {
  name = "${var.project}/${var.environment}/groq-api-key"

  tags = {
    Name = "${var.project}-${var.environment}-groq-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "groq_api_key" {
  secret_id     = aws_secretsmanager_secret.groq_api_key.id
  secret_string = jsonencode({ groq_api_key = var.groq_api_key })
}

resource "aws_secretsmanager_secret" "google_ai_api_key" {
  name = "${var.project}/${var.environment}/google-ai-api-key"

  tags = {
    Name = "${var.project}-${var.environment}-google-ai-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "google_ai_api_key" {
  secret_id     = aws_secretsmanager_secret.google_ai_api_key.id
  secret_string = jsonencode({ google_ai_api_key = var.google_ai_api_key })
}

# --- IAM Roles -------------------------------------------------------------

resource "aws_iam_role" "ecs_instance" {
  name = "${var.project}-${var.environment}-ecs-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance" {
  role       = aws_iam_role.ecs_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance" {
  name = "${var.project}-${var.environment}-ecs-instance"
  role = aws_iam_role.ecs_instance.name
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project}-${var.environment}-ecs-task-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${var.project}-${var.environment}-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/*"
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${var.project}-${var.environment}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project}-${var.environment}-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [var.s3_bucket_arn, "${var.s3_bucket_arn}/*"]
    }]
  })
}

# --- ECS Cluster -----------------------------------------------------------

resource "aws_ecs_cluster" "this" {
  name = "${var.project}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "${var.project}-${var.environment}"
  }
}

# --- EC2 Auto Scaling Group ------------------------------------------------

data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_launch_template" "ecs" {
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = var.instance_type
  iam_instance_profile { arn = aws_iam_instance_profile.ecs_instance.arn }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    echo ECS_CLUSTER=${aws_ecs_cluster.this.name} >> /etc/ecs/ecs.config
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project}-${var.environment}-ecs"
    }
  }
}

resource "aws_autoscaling_group" "ecs" {
  name                = "${var.project}-${var.environment}-ecs"
  vpc_zone_identifier = var.private_subnet_ids
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project}-${var.environment}-ecs"
    propagate_at_launch = true
  }
}

# --- CloudWatch Log Groups -------------------------------------------------

resource "aws_cloudwatch_log_group" "bot" {
  name              = "/ecs/${var.project}/${var.environment}/bot"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project}/${var.environment}/worker"
  retention_in_days = 30
}

# --- Task Definitions -------------------------------------------------------

resource "aws_ecs_task_definition" "bot" {
  family                   = "${var.project}-${var.environment}-bot"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "bot"
    image     = var.bot_image
    essential = true
    cpu       = 256
    memory    = 512

    environment = [
      { name = "TH_REDIS_URL", value = var.redis_url },
      { name = "TH_S3_BUCKET", value = var.s3_bucket_name },
      { name = "TH_COVER_LETTER_PROVIDER", value = "auto" },
      { name = "TH_RESUME_PROVIDER", value = "auto" },
      { name = "TH_JOB_DESCRIPTION_PROVIDER", value = "auto" },
    ]

    secrets = [
      { name = "TH_TELEGRAM_TOKEN", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/telegram-token:telegram_token::" },
      { name = "TH_DATABASE_URL", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/database-url:database_url::" },
      { name = "TH_GROQ_API_KEY", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/groq-api-key:groq_api_key::" },
      { name = "TH_GOOGLE_AI_API_KEY", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/google-ai-api-key:google_ai_api_key::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.bot.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "bot"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project}-${var.environment}-worker"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "worker"
    image     = var.worker_image
    essential = true
    cpu       = 256
    memory    = 512

    environment = [
      { name = "TH_REDIS_URL", value = var.redis_url },
      { name = "TH_S3_BUCKET", value = var.s3_bucket_name },
      { name = "TH_COVER_LETTER_PROVIDER", value = "auto" },
      { name = "TH_RESUME_PROVIDER", value = "auto" },
      { name = "TH_JOB_DESCRIPTION_PROVIDER", value = "auto" },
    ]

    secrets = [
      { name = "TH_DATABASE_URL", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/database-url:database_url::" },
      { name = "TH_GROQ_API_KEY", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/groq-api-key:groq_api_key::" },
      { name = "TH_GOOGLE_AI_API_KEY", valueFrom = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project}/${var.environment}/google-ai-api-key:google_ai_api_key::" },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

# --- ECS Services ----------------------------------------------------------

resource "aws_ecs_service" "bot" {
  name            = "${var.project}-${var.environment}-bot"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.bot.arn
  desired_count   = var.bot_desired_count
  launch_type     = "EC2"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}

resource "aws_ecs_service" "worker" {
  name            = "${var.project}-${var.environment}-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "EC2"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}
