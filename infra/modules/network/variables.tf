// Variáveis do módulo de rede (VPC dedicada e endpoints privados)
variable "project_name" {
  description = "Nome lógico do projeto para compor nomes de recursos de rede."
  type        = string
}

variable "aws_region" {
  description = "Região AWS usada para construção de endpoints VPC."
  type        = string
}

variable "vpc_cidr" {
  description = "Bloco CIDR da VPC dedicada da PoC."
  type        = string
}

variable "private_subnets_cidrs" {
  description = "Lista de CIDRs usados para as subnets privadas."
  type        = list(string)
}

