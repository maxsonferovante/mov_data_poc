// Outputs do módulo Observability (mantido simples na PoC)

output "ecs_log_group_name" {
  description = "Nome do log group do ECS."
  value       = var.ecs_log_group_name
}

output "step_functions_log_group_arn" {
  description = "ARN do log group do Step Functions."
  value       = var.step_functions_log_group_arn
}

