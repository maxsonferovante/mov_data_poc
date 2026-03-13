// Módulo S3: buckets de origem e destino com versionamento e SSE-KMS gerenciado pela AWS

locals {
  source_bucket_name = "${var.project_name}-source"
  target_bucket_name = "${var.project_name}-target"
}

resource "aws_s3_bucket" "source" {
  bucket = local.source_bucket_name

  // Permite destruir o bucket mesmo contendo objetos/versões (usado apenas para PoC)
  force_destroy = true

  tags = {
    Name        = local.source_bucket_name
    Environment = "poc"
    Role        = "source"
  }
}

resource "aws_s3_bucket" "target" {
  bucket = local.target_bucket_name

  // Permite destruir o bucket mesmo contendo objetos/versões (usado apenas para PoC)
  force_destroy = true

  tags = {
    Name        = local.target_bucket_name
    Environment = "poc"
    Role        = "target"
  }
}

// Versionamento habilitado nos buckets
resource "aws_s3_bucket_versioning" "source" {
  bucket = aws_s3_bucket.source.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "target" {
  bucket = aws_s3_bucket.target.id

  versioning_configuration {
    status = "Enabled"
  }
}

// Criptografia padrão SSE-KMS usando chave gerenciada pela AWS para S3
resource "aws_s3_bucket_server_side_encryption_configuration" "source" {
  bucket = aws_s3_bucket.source.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "target" {
  bucket = aws_s3_bucket.target.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

// Bloqueio de acesso público por segurança (apenas IAM)
resource "aws_s3_bucket_public_access_block" "source" {
  bucket = aws_s3_bucket.source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "target" {
  bucket = aws_s3_bucket.target.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

