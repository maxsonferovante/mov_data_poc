// Módulo Step Functions: state machine que dispara tasks ECS Fargate com parâmetros de buckets/prefixos

locals {
  state_machine_name = "${var.project_name}-data-mover-sm"
  log_group_name     = "/aws/states/${var.project_name}-data-mover"
  container_name     = "data-mover" // deve bater com o nome definido na task ECS
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = local.log_group_name
  retention_in_days = 14

  tags = {
    Name        = local.log_group_name
    Environment = "poc"
  }
}

// Role do Step Functions com permissão para executar RunTask no ECS e passar roles necessárias
resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "states.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions_ecs" {
  name = "${var.project_name}-step-functions-ecs"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowRunEcsTask",
        Effect = "Allow",
        Action = [
          "ecs:RunTask",
          "ecs:DescribeTasks"
        ],
        Resource = [
          var.ecs_task_definition_arn
        ]
      },
      {
        Sid    = "AllowUseCluster",
        Effect = "Allow",
        Action = [
          "ecs:DescribeClusters"
        ],
        Resource = [
          var.ecs_cluster_arn
        ]
      },
      {
        Sid    = "AllowPassRolesToEcs",
        Effect = "Allow",
        Action = [
          "iam:PassRole"
        ],
        Resource = [
          var.ecs_task_execution_role_arn,
          var.ecs_task_role_arn
        ]
      },
      {
        Sid    = "AllowEventsForRunTaskSync",
        Effect = "Allow",
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ],
        Resource = "*"
      },
      {
        Sid    = "AllowLogsForStateMachine",
        Effect = "Allow",
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ],
        Resource = "*"
      }
    ]
  })
}

// Definição da state machine em JSON: recebe buckets/prefixos e chama ecs:runTask.sync
locals {
  state_machine_definition = jsonencode({
    Comment = "State machine da PoC para movimentacao de dados via ECS Fargate.",
    StartAt = "RunEcsTask",
    States = {
      RunEcsTask = {
        Type     = "Task",
        Resource = "arn:aws:states:::ecs:runTask.sync",
        Parameters = {
          LaunchType = "FARGATE",
          Cluster    = var.ecs_cluster_arn,
          TaskDefinition = var.ecs_task_definition_arn,
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = var.private_subnet_ids,
              SecurityGroups = [var.ecs_security_group_id],
              AssignPublicIp = "DISABLED"
            }
          },
          Overrides = {
            ContainerOverrides = [
              {
                Name = local.container_name,
                Environment = [
                  // Passa os parâmetros de buckets e prefixos para variáveis de ambiente da task
                  {
                    Name      = "SOURCE_BUCKET",
                    "Value.$" = "$.source_bucket"
                  },
                  {
                    Name      = "SOURCE_PREFIX",
                    "Value.$" = "$.source_prefix"
                  },
                  {
                    Name      = "TARGET_BUCKET",
                    "Value.$" = "$.target_bucket"
                  },
                  {
                    Name      = "TARGET_PREFIX",
                    "Value.$" = "$.target_prefix"
                  }
                ]
              }
            ]
          }
        },
        End = true
      }
    }
  })
}

resource "aws_sfn_state_machine" "data_mover" {
  name     = local.state_machine_name
  role_arn = aws_iam_role.step_functions.arn
  type     = "STANDARD"

  definition = local.state_machine_definition

  timeouts {
    delete = "60m" // State machine pode demorar para apagar; aumenta timeout para reduzir falhas no destroy.
  }

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"

    log_destination = "${aws_cloudwatch_log_group.step_functions.arn}:*"
  }

  tags = {
    Name        = local.state_machine_name
    Environment = "poc"
  }
}

