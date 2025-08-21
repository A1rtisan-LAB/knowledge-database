# Main Terraform configuration for Knowledge Database on AWS

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration for state management
  backend "s3" {
    bucket = "knowledge-database-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "ap-northeast-2"  # Seoul region
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "knowledge-database"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  
  availability_zones = var.availability_zones
}

# RDS PostgreSQL
module "rds" {
  source = "./modules/rds"
  
  environment            = var.environment
  vpc_id                = module.vpc.vpc_id
  database_subnet_ids   = module.vpc.private_subnet_ids
  
  db_instance_class     = var.db_instance_class
  allocated_storage     = var.db_allocated_storage
  
  database_name         = "knowledge_prod"
  database_username     = var.db_username
  database_password     = var.db_password
  
  backup_retention_period = 7
  multi_az               = var.environment == "production"
}

# OpenSearch Domain
module "opensearch" {
  source = "./modules/opensearch"
  
  environment         = var.environment
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  
  instance_type      = var.opensearch_instance_type
  instance_count     = var.opensearch_instance_count
  
  ebs_volume_size    = var.opensearch_volume_size
  
  master_user_name   = var.opensearch_master_user
  master_user_password = var.opensearch_master_password
}

# ElastiCache Redis
module "redis" {
  source = "./modules/elasticache"
  
  environment           = var.environment
  vpc_id               = module.vpc.vpc_id
  subnet_ids           = module.vpc.private_subnet_ids
  
  node_type            = var.redis_node_type
  num_cache_nodes      = var.redis_num_nodes
  
  auth_token           = var.redis_auth_token
}

# ECS Fargate Cluster
module "ecs" {
  source = "./modules/ecs"
  
  environment          = var.environment
  vpc_id              = module.vpc.vpc_id
  
  public_subnet_ids   = module.vpc.public_subnet_ids
  private_subnet_ids  = module.vpc.private_subnet_ids
  
  task_cpu            = var.ecs_task_cpu
  task_memory         = var.ecs_task_memory
  
  container_image     = var.container_image
  container_port      = 8000
  
  # Environment variables for the container
  container_environment = [
    {
      name  = "DATABASE_URL"
      value = module.rds.connection_string
    },
    {
      name  = "OPENSEARCH_HOST"
      value = module.opensearch.endpoint
    },
    {
      name  = "REDIS_HOST"
      value = module.redis.primary_endpoint
    },
    {
      name  = "ENVIRONMENT"
      value = var.environment
    }
  ]
  
  # Secrets from AWS Secrets Manager
  container_secrets = [
    {
      name      = "SECRET_KEY"
      valueFrom = aws_secretsmanager_secret.app_secret.arn
    },
    {
      name      = "REDIS_PASSWORD"
      valueFrom = aws_secretsmanager_secret.redis_password.arn
    }
  ]
  
  desired_count       = var.ecs_desired_count
  min_capacity        = var.ecs_min_capacity
  max_capacity        = var.ecs_max_capacity
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  environment        = var.environment
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnet_ids
  
  certificate_arn   = var.ssl_certificate_arn
  
  target_group_arn  = module.ecs.target_group_arn
}

# S3 Bucket for static files
module "s3" {
  source = "./modules/s3"
  
  environment = var.environment
  bucket_name = "${var.project_name}-static-${var.environment}"
}

# CloudFront CDN
module "cloudfront" {
  source = "./modules/cloudfront"
  
  environment        = var.environment
  s3_bucket_domain  = module.s3.bucket_domain_name
  alb_domain_name   = module.alb.dns_name
  
  price_class       = var.cloudfront_price_class
}

# Secrets Manager
resource "aws_secretsmanager_secret" "app_secret" {
  name = "${var.project_name}-app-secret-${var.environment}"
}

resource "aws_secretsmanager_secret" "redis_password" {
  name = "${var.project_name}-redis-password-${var.environment}"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = 30
}

# Outputs
output "app_url" {
  value = module.alb.dns_name
  description = "Application URL"
}

output "cloudfront_url" {
  value = module.cloudfront.domain_name
  description = "CloudFront CDN URL"
}

output "rds_endpoint" {
  value = module.rds.endpoint
  description = "RDS PostgreSQL endpoint"
  sensitive = true
}

output "opensearch_endpoint" {
  value = module.opensearch.endpoint
  description = "OpenSearch endpoint"
  sensitive = true
}