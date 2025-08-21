# Production Environment Terraform Configuration

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Backend configuration provided via CLI
    # bucket = "knowledge-database-terraform-state-ACCOUNT_ID"
    # key    = "production/terraform.tfstate"
    # region = "us-west-2"
    # dynamodb_table = "knowledge-database-terraform-locks"
    # encrypt = true
  }
}

# Use the main module configuration
module "infrastructure" {
  source = "../../"
  
  # Pass all variables from terraform.tfvars
  environment                      = var.environment
  aws_region                      = var.aws_region
  project_name                    = var.project_name
  project_owner                   = var.project_owner
  cost_center                     = var.cost_center
  
  # Network
  vpc_cidr                        = var.vpc_cidr
  availability_zones              = var.availability_zones
  public_subnet_cidrs             = var.public_subnet_cidrs
  private_subnet_cidrs            = var.private_subnet_cidrs
  database_subnet_cidrs           = var.database_subnet_cidrs
  
  # ECS
  ecs_task_cpu                    = var.ecs_task_cpu
  ecs_task_memory                 = var.ecs_task_memory
  ecs_desired_count               = var.ecs_desired_count
  ecs_min_capacity                = var.ecs_min_capacity
  ecs_max_capacity                = var.ecs_max_capacity
  container_port                  = var.container_port
  
  # RDS
  rds_instance_class              = var.rds_instance_class
  rds_allocated_storage           = var.rds_allocated_storage
  rds_max_allocated_storage       = var.rds_max_allocated_storage
  rds_engine_version              = var.rds_engine_version
  rds_backup_retention_period     = var.rds_backup_retention_period
  rds_backup_window               = var.rds_backup_window
  rds_maintenance_window          = var.rds_maintenance_window
  
  # OpenSearch
  opensearch_instance_type        = var.opensearch_instance_type
  opensearch_instance_count       = var.opensearch_instance_count
  opensearch_volume_size          = var.opensearch_volume_size
  opensearch_version              = var.opensearch_version
  
  # ElastiCache
  elasticache_node_type           = var.elasticache_node_type
  elasticache_num_cache_nodes     = var.elasticache_num_cache_nodes
  elasticache_engine_version      = var.elasticache_engine_version
  
  # Auto Scaling
  cpu_target_value                = var.cpu_target_value
  memory_target_value             = var.memory_target_value
  scale_in_cooldown               = var.scale_in_cooldown
  scale_out_cooldown              = var.scale_out_cooldown
  
  # CloudWatch
  log_retention_days              = var.log_retention_days
  enable_detailed_monitoring      = var.enable_detailed_monitoring
  
  # S3
  s3_versioning_enabled           = var.s3_versioning_enabled
  s3_lifecycle_enabled            = var.s3_lifecycle_enabled
  s3_transition_days              = var.s3_transition_days
  s3_expiration_days              = var.s3_expiration_days
  
  # Feature Flags
  enable_deletion_protection      = var.enable_deletion_protection
  enable_encryption               = var.enable_encryption
  enable_multi_az                 = var.enable_multi_az
  enable_performance_insights     = var.enable_performance_insights
  enable_enhanced_monitoring      = var.enable_enhanced_monitoring
  enable_spot_instances           = var.enable_spot_instances
  
  # Domain
  domain_name                     = var.domain_name
  certificate_arn                 = var.certificate_arn
}

# Outputs
output "deployment_info" {
  value = {
    ecr_repository_url    = module.infrastructure.ecr_repository_url
    alb_dns_name         = module.infrastructure.alb_dns_name
    ecs_cluster_name     = module.infrastructure.ecs_cluster_name
    ecs_service_name     = module.infrastructure.ecs_service_name
    s3_bucket_name       = module.infrastructure.s3_bucket_name
    dashboard_url        = module.infrastructure.cloudwatch_dashboard_url
  }
}

output "private_subnet_ids" {
  value = module.infrastructure.private_subnet_ids
}

output "ecs_security_group_id" {
  value = module.infrastructure.ecs_security_group_id
}