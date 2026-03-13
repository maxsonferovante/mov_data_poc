// Outputs principais do módulo ECS para integração com Step Functions e observabilidade

output "cluster_arn" {
  description = "ARN do cluster ECS Fargate."
  value       = aws_ecs_cluster.this.arn
}

output "task_definition_arn" {
  description = "ARN da task definition Fargate de movimentação."
  value       = aws_ecs_task_definition.data_mover.arn
}

output "log_group_name" {
  description = "Nome do CloudWatch Log Group usado pelas tasks ECS."
  value       = aws_cloudwatch_log_group.ecs.name
}

output "task_execution_role_arn" {
  description = "ARN da role de execução da task ECS."
  value       = aws_iam_role.ecs_task_execution.arn
}

output "task_role_arn" {
  description = "ARN da role de aplicação da task ECS."
  value       = aws_iam_role.ecs_task.arn
}

output "task_security_group_id" {
  description = "Security group associado às tasks ECS Fargate."
  value       = aws_security_group.tasks.id
}

output "ecr_repository_url" {
  description = "URL do repositório ECR usado pela aplicação de movimentação."
  value       = aws_ecr_repository.app.repository_url
}


