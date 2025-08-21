# CloudWatch Monitoring Module

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  count = var.alarm_email != "" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name = "${var.project_name}-${var.environment}-alerts"
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU %" }],
            [".", "MemoryUtilization", { stat = "Average", label = "Memory %" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "ECS Resource Utilization"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average", label = "Response Time (ms)" }],
            [".", "RequestCount", { stat = "Sum", label = "Request Count" }],
            [".", "HTTPCode_Target_2XX_Count", { stat = "Sum", label = "2XX Responses" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum", label = "5XX Errors" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Application Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "DatabaseConnections", { stat = "Average", label = "DB Connections" }],
            [".", "CPUUtilization", { stat = "Average", label = "DB CPU %" }],
            [".", "FreeableMemory", { stat = "Average", label = "Free Memory (MB)" }],
            [".", "ReadLatency", { stat = "Average", label = "Read Latency (ms)" }],
            [".", "WriteLatency", { stat = "Average", label = "Write Latency (ms)" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "RDS Database Metrics"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", { stat = "Average", label = "Redis CPU %" }],
            [".", "DatabaseMemoryUsagePercentage", { stat = "Average", label = "Memory Usage %" }],
            [".", "CacheHits", { stat = "Sum", label = "Cache Hits" }],
            [".", "CacheMisses", { stat = "Sum", label = "Cache Misses" }],
            [".", "Evictions", { stat = "Sum", label = "Evictions" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Redis Cache Metrics"
          period  = 300
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '/ecs/${var.project_name}-${var.environment}' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = data.aws_region.current.name
          title   = "Recent Errors"
        }
      }
    ]
  })
}

data "aws_region" "current" {}

# ECS Alarms
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  alarm_name          = "${var.project_name}-${var.environment}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS memory utilization"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ecs-memory-alarm"
  }
}

# ALB Alarms
resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_hosts" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-unhealthy-hosts"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Alert when we have unhealthy hosts"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-unhealthy-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_response_time" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Average"
  threshold           = "2"
  alarm_description   = "Alert when response time is too high"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-response-time-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert on high 5XX error rate"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  treat_missing_data  = "notBreaching"

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-5xx-alarm"
  }
}

# Custom Metrics Namespace
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "${var.project_name}-${var.environment}-error-count"
  log_group_name = "/ecs/${var.project_name}-${var.environment}"
  pattern        = "[ERROR]"

  metric_transformation {
    name      = "ErrorCount"
    namespace = "${var.project_name}/${var.environment}"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "application_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-application-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorCount"
  namespace           = "${var.project_name}/${var.environment}"
  period              = "300"
  statistic           = "Sum"
  threshold           = "50"
  alarm_description   = "Alert on high application error rate"
  alarm_actions       = var.alarm_email != "" ? [aws_sns_topic.alerts[0].arn] : []
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.project_name}-${var.environment}-app-errors-alarm"
  }
}

# Log Insights Queries
resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "${var.project_name}-${var.environment}-error-analysis"

  log_group_names = [
    "/ecs/${var.project_name}-${var.environment}"
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
EOF
}

resource "aws_cloudwatch_query_definition" "performance_analysis" {
  name = "${var.project_name}-${var.environment}-performance-analysis"

  log_group_names = [
    "/ecs/${var.project_name}-${var.environment}"
  ]

  query_string = <<EOF
fields @timestamp, @message
| filter @message like /response_time/
| parse @message /response_time=(?<responseTime>\d+)/
| stats avg(responseTime) as avg_response_time,
        max(responseTime) as max_response_time,
        min(responseTime) as min_response_time
        by bin(5m)
EOF
}

# EventBridge Rule for Deployment Events
resource "aws_cloudwatch_event_rule" "deployment_events" {
  name        = "${var.project_name}-${var.environment}-deployment-events"
  description = "Capture ECS deployment events"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Service Action", "ECS Task State Change"]
    detail = {
      clusterArn = ["arn:aws:ecs:*:*:cluster/${var.ecs_cluster_name}"]
    }
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-deployment-events"
  }
}

resource "aws_cloudwatch_event_target" "sns" {
  count     = var.alarm_email != "" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.deployment_events.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.alerts[0].arn
}

# CloudWatch Synthetics Canary (Optional)
resource "aws_synthetics_canary" "health_check" {
  count                = var.enable_detailed_monitoring ? 1 : 0
  name                 = "${var.project_name}-${var.environment}-health"
  artifact_s3_location = "s3://${aws_s3_bucket.canary_artifacts[0].id}"
  execution_role_arn   = aws_iam_role.canary[0].arn
  handler             = "apiCanary.handler"
  zip_file            = data.archive_file.canary_code[0].output_path
  runtime_version     = "syn-nodejs-puppeteer-3.9"
  start_canary        = true

  schedule {
    expression = "rate(5 minutes)"
  }

  run_config {
    timeout_in_seconds = 60
    memory_in_mb      = 960
  }

  success_retention_period_in_days = 2
  failure_retention_period_in_days = 14

  tags = {
    Name = "${var.project_name}-${var.environment}-canary"
  }
}

# S3 Bucket for Canary Artifacts
resource "aws_s3_bucket" "canary_artifacts" {
  count  = var.enable_detailed_monitoring ? 1 : 0
  bucket = "${var.project_name}-${var.environment}-canary-artifacts"

  tags = {
    Name = "${var.project_name}-${var.environment}-canary-artifacts"
  }
}

# IAM Role for Canary
resource "aws_iam_role" "canary" {
  count = var.enable_detailed_monitoring ? 1 : 0
  name  = "${var.project_name}-${var.environment}-canary-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Canary code archive
data "archive_file" "canary_code" {
  count       = var.enable_detailed_monitoring ? 1 : 0
  type        = "zip"
  output_path = "/tmp/canary.zip"
  
  source {
    content  = <<EOF
const synthetics = require('Synthetics');
const log = require('SyntheticsLogger');

const apiCanaryBlueprint = async function () {
    const page = await synthetics.getPage();
    
    const response = await page.goto('https://${var.alb_dns_name}/health', {
        waitUntil: 'networkidle0',
        timeout: 30000,
    });
    
    if (!response) {
        throw new Error('No response from health endpoint');
    }
    
    const statusCode = response.status();
    
    if (statusCode !== 200) {
        throw new Error(`Health check failed with status: ${statusCode}`);
    }
    
    log.info('Health check passed');
};

exports.handler = async () => {
    return await synthetics.executeBlueprint(apiCanaryBlueprint);
};
EOF
    filename = "apiCanary.js"
  }
}