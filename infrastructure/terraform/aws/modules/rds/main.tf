# RDS PostgreSQL Module with pgvector Extension

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}"
  subnet_ids = var.database_subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet-group"
  }
}

# DB Parameter Group with pgvector
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-pg15"
  family = "postgres15"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,pgaudit,pgvector"
  }

  parameter {
    name  = "log_statement"
    value = "all"
  }

  parameter {
    name  = "log_duration"
    value = "1"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries taking more than 1 second
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/4}"
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory*3/4}"
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "2097152"  # 2GB in KB
  }

  parameter {
    name  = "work_mem"
    value = "16384"  # 16MB in KB
  }

  parameter {
    name  = "random_page_cost"
    value = "1.1"  # SSD optimized
  }

  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-db-params"
  }
}

# DB Option Group
resource "aws_db_option_group" "main" {
  name                     = "${var.project_name}-${var.environment}-options"
  option_group_description = "Option group for ${var.project_name} ${var.environment}"
  engine_name              = "postgres"
  major_engine_version     = "15"

  tags = {
    Name = "${var.project_name}-${var.environment}-db-options"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Random password for RDS
resource "random_password" "rds" {
  length  = 32
  special = true
}

# KMS Key for RDS Encryption
resource "aws_kms_key" "rds" {
  count                   = var.enable_encryption ? 1 : 0
  description             = "KMS key for RDS encryption - ${var.project_name}-${var.environment}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-kms"
  }
}

resource "aws_kms_alias" "rds" {
  count         = var.enable_encryption ? 1 : 0
  name          = "alias/${var.project_name}-${var.environment}-rds"
  target_key_id = aws_kms_key.rds[0].key_id
}

# RDS Instance (Primary)
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}"
  engine         = "postgres"
  engine_version = var.rds_engine_version
  instance_class = var.rds_instance_class

  allocated_storage     = var.rds_allocated_storage
  max_allocated_storage = var.rds_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = var.enable_encryption
  kms_key_id           = var.enable_encryption ? aws_kms_key.rds[0].arn : null
  iops                 = 3000
  storage_throughput   = 125

  db_name  = replace(var.project_name, "-", "_")
  username = "dbadmin"
  password = random_password.rds.result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  option_group_name      = aws_db_option_group.main.name

  backup_retention_period = var.rds_backup_retention_period
  backup_window          = var.rds_backup_window
  maintenance_window     = var.rds_maintenance_window

  multi_az               = var.enable_multi_az
  publicly_accessible    = false
  deletion_protection    = var.enable_deletion_protection
  skip_final_snapshot    = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  performance_insights_enabled    = var.enable_performance_insights
  performance_insights_retention_period = var.enable_performance_insights ? 7 : null
  performance_insights_kms_key_id = var.enable_performance_insights && var.enable_encryption ? aws_kms_key.rds[0].arn : null

  monitoring_interval = var.enable_enhanced_monitoring ? 60 : 0
  monitoring_role_arn = var.enable_enhanced_monitoring ? aws_iam_role.rds_monitoring[0].arn : null

  auto_minor_version_upgrade = false
  apply_immediately         = var.environment != "production"

  tags = {
    Name = "${var.project_name}-${var.environment}-rds"
  }

  depends_on = [
    aws_db_subnet_group.main,
    aws_security_group.rds
  ]
}

# RDS Read Replica (for production)
resource "aws_db_instance" "read_replica" {
  count                    = var.environment == "production" && var.enable_read_replica ? 1 : 0
  identifier               = "${var.project_name}-${var.environment}-read-replica"
  replicate_source_db      = aws_db_instance.main.identifier
  instance_class           = var.rds_instance_class
  
  storage_encrypted        = var.enable_encryption
  kms_key_id              = var.enable_encryption ? aws_kms_key.rds[0].arn : null
  
  publicly_accessible      = false
  auto_minor_version_upgrade = false
  
  performance_insights_enabled = var.enable_performance_insights
  monitoring_interval         = var.enable_enhanced_monitoring ? 60 : 0
  monitoring_role_arn        = var.enable_enhanced_monitoring ? aws_iam_role.rds_monitoring[0].arn : null

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-read-replica"
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  count = var.enable_enhanced_monitoring ? 1 : 0
  name  = "${var.project_name}-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-monitoring-role"
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.enable_enhanced_monitoring ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Alarms for RDS
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240"  # 10 GB in bytes
  alarm_description   = "This metric monitors RDS free storage"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-storage-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "180"  # 90% of max_connections (200)
  alarm_description   = "This metric monitors RDS connection count"
  alarm_actions       = var.sns_topic_arn != "" ? [var.sns_topic_arn] : []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-connections-alarm"
  }
}

# Store RDS credentials in Secrets Manager
resource "aws_secretsmanager_secret" "rds_credentials" {
  name                    = "${var.project_name}-${var.environment}-rds-credentials"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "rds_credentials" {
  secret_id = aws_secretsmanager_secret.rds_credentials.id
  
  secret_string = jsonencode({
    username = aws_db_instance.main.username
    password = random_password.rds.result
    engine   = "postgres"
    host     = aws_db_instance.main.address
    port     = aws_db_instance.main.port
    dbname   = aws_db_instance.main.db_name
  })
}

# Database URL Secret for ECS
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.project_name}-${var.environment}-database-url"
  recovery_window_in_days = var.environment == "production" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-database-url"
  }
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  
  secret_string = "postgresql://${aws_db_instance.main.username}:${random_password.rds.result}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
}