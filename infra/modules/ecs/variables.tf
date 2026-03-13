// Variáveis do módulo ECS (cluster Fargate e task definition)
variable "project_name" {
  description = "Nome lógico do projeto para compor nomes de recursos ECS."
  type        = string
}

variable "aws_region" {
  description = "Região AWS usada para integrações IAM e logs."
  type        = string
}

variable "vpc_id" {
  description = "ID da VPC onde as tasks Fargate serão executadas."
  type        = string
}

variable "private_subnet_ids" {
  description = "Lista de subnets privadas usadas pelas tasks Fargate."
  type        = list(string)
}

variable "source_bucket_arn" {
  description = "ARN do bucket S3 de origem."
  type        = string
}

variable "target_bucket_arn" {
  description = "ARN do bucket S3 de destino."
  type        = string
}

variable "image_tag" {
  description = "Tag da imagem da aplicação no ECR usada pela task ECS."
  type        = string
  default     = "latest"
}


