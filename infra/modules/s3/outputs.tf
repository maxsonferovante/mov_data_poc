// Outputs dos buckets S3 de origem e destino

output "source_bucket_name" {
  description = "Nome do bucket S3 de origem."
  value       = aws_s3_bucket.source.bucket
}

output "target_bucket_name" {
  description = "Nome do bucket S3 de destino."
  value       = aws_s3_bucket.target.bucket
}

output "source_bucket_arn" {
  description = "ARN do bucket S3 de origem."
  value       = aws_s3_bucket.source.arn
}

output "target_bucket_arn" {
  description = "ARN do bucket S3 de destino."
  value       = aws_s3_bucket.target.arn
}

