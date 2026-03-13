// Outputs principais de rede para consumo pelos outros módulos

output "vpc_id" {
  description = "ID da VPC dedicada da PoC."
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "Lista de subnets privadas usadas pelo ECS Fargate."
  value       = aws_subnet.private[*].id
}

output "endpoints_security_group_id" {
  description = "Security group usado pelos endpoints de interface."
  value       = aws_security_group.endpoints.id
}

