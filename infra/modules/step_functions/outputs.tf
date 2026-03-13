// Outputs principais do módulo Step Functions

output "state_machine_arn" {
  description = "ARN da state machine que orquestra a movimentação de dados."
  value       = aws_sfn_state_machine.data_mover.arn
}

output "log_group_arn" {
  description = "ARN do log group usado pela state machine."
  value       = aws_cloudwatch_log_group.step_functions.arn
}

