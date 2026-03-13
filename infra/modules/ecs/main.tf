// Módulo ECS: cluster Fargate e task definition genérica para movimentação de dados

data "aws_caller_identity" "current" {}

locals {
  cluster_name    = "${var.project_name}-ecs-cluster"
  task_family     = "${var.project_name}-data-mover"
  log_group_name  = "/ecs/${var.project_name}-data-mover"
  container_name  = "data-mover"
  // ARN base de recursos KMS na conta (para permitir uso das chaves gerenciadas da AWS)
  kms_arn_prefix = "arn:aws:kms:${var.aws_region}:${data.aws_caller_identity.current.account_id}:key/*"
}

resource "aws_ecr_repository" "app" {
  name = "${var.project_name}-app"

  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  // Permite destruir o repositório mesmo contendo imagens (usado apenas para PoC)
  force_delete = true

  tags = {
    Name        = "${var.project_name}-app-ecr"
    Environment = "poc"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = local.log_group_name
  retention_in_days = 14

  tags = {
    Name        = local.log_group_name
    Environment = "poc"
  }
}

resource "aws_ecs_cluster" "this" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = local.cluster_name
    Environment = "poc"
  }
}

// Security group para as tasks Fargate (acesso apenas dentro da VPC)
resource "aws_security_group" "tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group para tasks ECS Fargate da PoC."
  vpc_id      = var.vpc_id

  // Saída apenas para dentro da VPC (sem internet)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ecs-tasks-sg"
    Environment = "poc"
  }
}

// Role de execução da task ECS (puxa imagem do ECR, escreve logs, etc.)
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

// Policy gerenciada padrão da AWS para execução de tasks ECS (logs, ECR, etc.)
resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

// Role da aplicação da task ECS (acesso aos buckets S3 e KMS)
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

// Policy mínima para leitura do bucket de origem, escrita no bucket de destino e uso de KMS
resource "aws_iam_role_policy" "ecs_task_s3_kms" {
  name = "${var.project_name}-ecs-task-s3-kms"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowReadFromSourceBucket",
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          var.source_bucket_arn,
          "${var.source_bucket_arn}/*"
        ]
      },
      {
        Sid    = "AllowWriteToTargetBucket",
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Resource = [
          var.target_bucket_arn,
          "${var.target_bucket_arn}/*"
        ]
      },
      {
        Sid    = "AllowUseOfKmsForS3",
        Effect = "Allow",
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = local.kms_arn_prefix
      }
    ]
  })
}

// Task definition genérica Fargate para movimentação (imagem placeholder)
resource "aws_ecs_task_definition" "data_mover" {
  family                   = local.task_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "2048"

  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = local.container_name,
      image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}",
      essential = true,
      environment = [
        // Esses valores serão sobrescritos pelo Step Functions via overrides
        {
          name  = "SOURCE_BUCKET",
          value = ""
        },
        {
          name  = "SOURCE_PREFIX",
          value = ""
        },
        {
          name  = "TARGET_BUCKET",
          value = ""
        },
        {
          name  = "TARGET_PREFIX",
          value = ""
        }
      ],
      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-region        = var.aws_region,
          awslogs-group         = local.log_group_name,
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = {
    Name        = local.task_family
    Environment = "poc"
  }
}

