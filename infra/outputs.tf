// Outputs principais da PoC

output "vpc_id" {
  description = "ID da VPC criada para a PoC."
  value       = module.network.vpc_id
}

output "private_subnet_ids" {
  description = "Subnets privadas usadas pelo ECS Fargate."
  value       = module.network.private_subnet_ids
}

output "source_bucket_name" {
  description = "Nome do bucket S3 de origem."
  value       = module.s3.source_bucket_name
}

output "target_bucket_name" {
  description = "Nome do bucket S3 de destino."
  value       = module.s3.target_bucket_name
}

output "ecs_cluster_arn" {
  description = "ARN do cluster ECS Fargate."
  value       = module.ecs.cluster_arn
}

output "ecs_task_definition_arn" {
  description = "ARN da task definition Fargate usada pelas movimentações."
  value       = module.ecs.task_definition_arn
}

output "step_functions_state_machine_arn" {
  description = "ARN da State Machine do Step Functions responsável por orquestrar as tarefas ECS."
  value       = module.step_functions.state_machine_arn
}

