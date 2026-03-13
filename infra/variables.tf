// Variáveis globais da PoC
variable "aws_region" {
  description = "Região AWS onde a PoC será criada."
  type        = string
}

variable "project_name" {
  description = "Nome lógico do projeto para composição dos recursos."
  type        = string
  default     = "mov-poc"
}

variable "vpc_cidr" {
  description = "CIDR da VPC dedicada da PoC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "private_subnets_cidrs" {
  description = "Lista de CIDRs para subnets privadas em múltiplas AZs."
  type        = list(string)
  default     = ["10.20.1.0/24", "10.20.2.0/24"]
}

