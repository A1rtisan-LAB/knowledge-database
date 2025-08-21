variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecr_repository_url" {
  description = "ECR repository URL"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task"
  type        = number
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = number
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
}

variable "ecs_min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
}

variable "ecs_max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
}

variable "container_port" {
  description = "Container port"
  type        = number
}

variable "alb_target_group_arn" {
  description = "ALB target group ARN"
  type        = string
}

variable "alb_listener_arn" {
  description = "ALB listener ARN"
  type        = string
}

variable "alb_security_group_id" {
  description = "ALB security group ID"
  type        = string
}

variable "database_url_secret_arn" {
  description = "ARN of the database URL secret"
  type        = string
}

variable "redis_url_secret_arn" {
  description = "ARN of the Redis URL secret"
  type        = string
}

variable "opensearch_url_secret_arn" {
  description = "ARN of the OpenSearch URL secret"
  type        = string
}

variable "jwt_secret_arn" {
  description = "ARN of the JWT secret"
  type        = string
}

variable "secret_key_arn" {
  description = "ARN of the application secret key"
  type        = string
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN for application storage"
  type        = string
}

variable "cpu_target_value" {
  description = "Target CPU utilization for auto scaling"
  type        = number
}

variable "memory_target_value" {
  description = "Target memory utilization for auto scaling"
  type        = number
}

variable "scale_in_cooldown" {
  description = "Scale in cooldown period in seconds"
  type        = number
}

variable "scale_out_cooldown" {
  description = "Scale out cooldown period in seconds"
  type        = number
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
}

variable "enable_spot_instances" {
  description = "Enable Spot instances for ECS Fargate"
  type        = bool
  default     = false
}