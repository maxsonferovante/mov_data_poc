// Variáveis do módulo Observability
variable "project_name" {
  description = "Nome lógico do projeto."
  type        = string
}

variable "ecs_log_group_name" {
  description = "Nome do log group do ECS."
  type        = string
}

variable "step_functions_log_group_arn" {
  description = "ARN do log group usado pelo Step Functions."
  type        = string
}

