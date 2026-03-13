// Orquestração dos módulos principais da PoC

module "network" {
  source = "./modules/network"

  project_name          = var.project_name
  aws_region            = var.aws_region
  vpc_cidr              = var.vpc_cidr
  private_subnets_cidrs = var.private_subnets_cidrs
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
}

module "ecs" {
  source = "./modules/ecs"

  project_name = var.project_name

  aws_region         = var.aws_region
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids

  source_bucket_arn = module.s3.source_bucket_arn
  target_bucket_arn = module.s3.target_bucket_arn
}

module "step_functions" {
  source = "./modules/step_functions"

  project_name = var.project_name

  aws_region = var.aws_region

  ecs_cluster_arn             = module.ecs.cluster_arn
  ecs_task_definition_arn     = module.ecs.task_definition_arn
  ecs_task_execution_role_arn = module.ecs.task_execution_role_arn
  ecs_task_role_arn           = module.ecs.task_role_arn

  private_subnet_ids    = module.network.private_subnet_ids
  ecs_security_group_id = module.ecs.task_security_group_id
}

module "observability" {
  source = "./modules/observability"

  project_name = var.project_name

  ecs_log_group_name           = module.ecs.log_group_name
  step_functions_log_group_arn = module.step_functions.log_group_arn
}

