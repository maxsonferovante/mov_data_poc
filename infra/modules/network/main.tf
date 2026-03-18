// Módulo de rede: VPC dedicada sem internet e endpoints privados

data "aws_availability_zones" "available" {
  // Usa AZs disponíveis na região para distribuir subnets privadas
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = "poc"
  }
}

resource "aws_subnet" "private" {
  count                   = length(var.private_subnets_cidrs)
  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.private_subnets_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = false

  tags = {
    Name        = "${var.project_name}-private-${count.index + 1}"
    Environment = "poc"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  // Apenas rota local, sem saída para internet; tráfego para serviços AWS vai via endpoints
  route {
    cidr_block = aws_vpc.this.cidr_block
    gateway_id = "local"
  }

  tags = {
    Name        = "${var.project_name}-rt-private"
    Environment = "poc"
  }
}

resource "aws_route_table_association" "private" {
  count          = length(aws_subnet.private)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

// Security group para endpoints de interface: permite acesso HTTPS a partir da VPC
resource "aws_security_group" "endpoints" {
  name        = "${var.project_name}-endpoints-sg"
  description = "SG para VPC Interface Endpoints"
  vpc_id      = aws_vpc.this.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.this.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.this.cidr_block]
  }

  tags = {
    Name        = "${var.project_name}-endpoints-sg"
    Environment = "poc"
  }
}

// Endpoint gateway para S3 (acesso privado aos buckets)
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id       = aws_vpc.this.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  vpc_endpoint_type = "Gateway"

  route_table_ids = [aws_route_table.private.id]

  tags = {
    Name        = "${var.project_name}-s3-endpoint"
    Environment = "poc"
  }
}

// Conjunto de endpoints de interface para serviços necessários (ECS, Logs, Step Functions, STS, ECR)
locals {
  interface_services = [
    "ecs",
    "ecs-agent",
    "ecs-telemetry",
    "logs",
    "states",
    "ecr.api",
    "ecr.dkr",
    "sts"
  ]
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset(local.interface_services)

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type = "Interface"

  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.endpoints.id]

  timeouts {
    delete = "60m" // Deleção de ENIs pode demorar; aumenta timeout para reduzir falhas em destroy.
  }

  tags = {
    Name        = "${var.project_name}-${each.key}-endpoint"
    Environment = "poc"
  }
}

