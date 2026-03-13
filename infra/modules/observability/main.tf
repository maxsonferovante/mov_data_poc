// Módulo Observability
// Para esta PoC, a maior parte da observabilidade (CloudWatch Logs) já é criada
// dentro dos módulos ECS e Step Functions. Este módulo fica como ponto de extensão
// para futuros alarms/metrics, mantendo a separação de responsabilidades.

locals {
  project_name = var.project_name
}

