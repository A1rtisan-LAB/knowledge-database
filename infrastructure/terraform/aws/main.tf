# Main Terraform Configuration - Knowledge Database AWS Infrastructure

# Data Sources
data "aws_caller_identity" "current" {}

# ECR Repository
resource "aws_ecr_repository" "main" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

# ECR Lifecycle Policy
resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images per environment"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["dev", "staging", "production"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name          = var.project_name
  environment          = var.environment
  aws_region           = var.aws_region
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  database_subnet_cidrs = var.database_subnet_cidrs
  log_retention_days   = var.log_retention_days
}

# Secrets Manager Secrets
resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "${var.project_name}-${var.environment}-jwt-secret"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-jwt-secret"
  }
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = random_password.jwt_secret.result
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "aws_secretsmanager_secret" "app_secret" {
  name                    = "${var.project_name}-${var.environment}-app-secret"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-app-secret"
  }
}

resource "aws_secretsmanager_secret_version" "app_secret" {
  secret_id     = aws_secretsmanager_secret.app_secret.id
  secret_string = random_password.app_secret.result
}

resource "random_password" "app_secret" {
  length  = 64
  special = true
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name           = var.project_name
  environment           = var.environment
  versioning_enabled    = var.s3_versioning_enabled
  lifecycle_enabled     = var.s3_lifecycle_enabled
  transition_days       = var.s3_transition_days
  expiration_days       = var.s3_expiration_days
  enable_encryption     = var.enable_encryption
}

# ALB Module
module "alb" {
  source = "./modules/alb"

  project_name                     = var.project_name
  environment                     = var.environment
  vpc_id                          = module.vpc.vpc_id
  public_subnet_ids               = module.vpc.public_subnet_ids
  certificate_arn                 = var.certificate_arn
  health_check_path               = var.health_check_path
  health_check_interval           = var.health_check_interval
  health_check_timeout            = var.health_check_timeout
  health_check_healthy_threshold   = var.health_check_healthy_threshold
  health_check_unhealthy_threshold = var.health_check_unhealthy_threshold
  idle_timeout                    = var.alb_idle_timeout
  enable_deletion_protection      = var.enable_deletion_protection
  container_port                  = var.container_port
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  project_name                = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  database_subnet_ids        = module.vpc.database_subnet_ids
  allowed_security_groups    = [module.ecs.ecs_security_group_id]
  rds_instance_class         = var.rds_instance_class
  rds_allocated_storage      = var.rds_allocated_storage
  rds_max_allocated_storage  = var.rds_max_allocated_storage
  rds_engine_version         = var.rds_engine_version
  rds_backup_retention_period = var.rds_backup_retention_period
  rds_backup_window          = var.rds_backup_window
  rds_maintenance_window     = var.rds_maintenance_window
  enable_encryption          = var.enable_encryption
  enable_multi_az            = var.enable_multi_az
  enable_deletion_protection = var.enable_deletion_protection
  enable_performance_insights = var.enable_performance_insights
  enable_enhanced_monitoring = var.enable_enhanced_monitoring
  enable_read_replica        = var.environment == "production"
  sns_topic_arn             = module.cloudwatch.sns_topic_arn
}

# OpenSearch Module
module "opensearch" {
  source = "./modules/opensearch"

  project_name              = var.project_name
  environment              = var.environment
  vpc_id                   = module.vpc.vpc_id
  private_subnet_ids       = module.vpc.private_subnet_ids
  allowed_security_groups  = [module.ecs.ecs_security_group_id]
  opensearch_version       = var.opensearch_version
  opensearch_instance_type = var.opensearch_instance_type
  opensearch_instance_count = var.opensearch_instance_count
  opensearch_volume_size   = var.opensearch_volume_size
  enable_encryption        = var.enable_encryption
  enable_multi_az          = var.enable_multi_az
}

# ElastiCache Module
module "elasticache" {
  source = "./modules/elasticache"

  project_name                = var.project_name
  environment                = var.environment
  vpc_id                     = module.vpc.vpc_id
  private_subnet_ids         = module.vpc.private_subnet_ids
  allowed_security_groups    = [module.ecs.ecs_security_group_id]
  elasticache_node_type      = var.elasticache_node_type
  elasticache_num_cache_nodes = var.elasticache_num_cache_nodes
  elasticache_engine_version = var.elasticache_engine_version
  enable_encryption          = var.enable_encryption
  enable_multi_az            = var.enable_multi_az
  sns_topic_arn             = module.cloudwatch.sns_topic_arn
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  project_name              = var.project_name
  environment              = var.environment
  aws_region               = var.aws_region
  vpc_id                   = module.vpc.vpc_id
  private_subnet_ids       = module.vpc.private_subnet_ids
  ecr_repository_url       = aws_ecr_repository.main.repository_url
  image_tag                = var.environment == "production" ? "production-latest" : "staging-latest"
  ecs_task_cpu             = var.ecs_task_cpu
  ecs_task_memory          = var.ecs_task_memory
  ecs_desired_count        = var.ecs_desired_count
  ecs_min_capacity         = var.ecs_min_capacity
  ecs_max_capacity         = var.ecs_max_capacity
  container_port           = var.container_port
  alb_target_group_arn     = module.alb.target_group_arn
  alb_listener_arn         = module.alb.https_listener_arn
  alb_security_group_id    = module.alb.security_group_id
  database_url_secret_arn  = module.rds.database_url_secret_arn
  redis_url_secret_arn     = module.elasticache.redis_url_secret_arn
  opensearch_url_secret_arn = module.opensearch.opensearch_url_secret_arn
  jwt_secret_arn           = aws_secretsmanager_secret.jwt_secret.arn
  secret_key_arn           = aws_secretsmanager_secret.app_secret.arn
  s3_bucket_arn            = module.s3.bucket_arn
  cpu_target_value         = var.cpu_target_value
  memory_target_value      = var.memory_target_value
  scale_in_cooldown        = var.scale_in_cooldown
  scale_out_cooldown       = var.scale_out_cooldown
  log_retention_days       = var.log_retention_days
  enable_spot_instances    = var.enable_spot_instances
}

# CloudWatch Module
module "cloudwatch" {
  source = "./modules/cloudwatch"

  project_name               = var.project_name
  environment               = var.environment
  log_retention_days        = var.log_retention_days
  enable_detailed_monitoring = var.enable_detailed_monitoring
  alarm_email               = var.environment == "production" ? var.alarm_email : ""
  ecs_cluster_name          = module.ecs.cluster_id
  ecs_service_name          = module.ecs.service_name
  alb_arn_suffix            = module.alb.alb_arn_suffix
  target_group_arn_suffix   = module.alb.target_group_arn_suffix
  rds_instance_identifier   = module.rds.db_instance_id
  elasticache_cluster_id    = module.elasticache.cluster_id
  opensearch_domain_name    = module.opensearch.domain_name
}

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.main.repository_url
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_id
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "opensearch_endpoint" {
  description = "OpenSearch domain endpoint"
  value       = module.opensearch.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.elasticache.primary_endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.cloudwatch.dashboard_url
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = module.ecs.ecs_security_group_id
}