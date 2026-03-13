// Variáveis do módulo Step Functions (state machine que orquestra ECS)
variable "project_name" {
  description = "Nome lógico do projeto para compor nomes da state machine."
  type        = string
}

variable "aws_region" {
  description = "Região AWS usada em ARNs e logs."
  type        = string
}

variable "ecs_cluster_arn" {
  description = "ARN do cluster ECS onde as tasks serão executadas."
  type        = string
}

variable "ecs_task_definition_arn" {
  description = "ARN da task definition Fargate usada para movimentação."
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ARN da role de execução da task ECS (passada pelo Step Functions)."
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN da role de aplicação da task ECS (passada pelo Step Functions)."
  type        = string
}

variable "private_subnet_ids" {
  description = "Lista de subnets privadas onde a task ECS será executada (awsvpc)."
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group usado pelas tasks ECS."
  type        = string
}

