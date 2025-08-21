# AWS Deployment Guide for Knowledge Database

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Infrastructure Overview](#infrastructure-overview)
4. [Deployment Steps](#deployment-steps)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Cost Optimization](#cost-optimization)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools
- AWS CLI v2.x configured with appropriate credentials
- Terraform >= 1.5.0
- Docker >= 20.x
- Git
- Python 3.11+

### AWS Account Setup
1. Create an AWS account with appropriate billing alerts
2. Configure IAM user with deployment permissions
3. Set up AWS CLI credentials:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-west-2
# Default output format: json
```

### Required AWS Permissions
The deployment user needs the following AWS service permissions:
- VPC (Full Access)
- ECS (Full Access)
- RDS (Full Access)
- OpenSearch (Full Access)
- ElastiCache (Full Access)
- S3 (Full Access)
- CloudWatch (Full Access)
- Secrets Manager (Full Access)
- IAM (Limited - Role and Policy creation)
- ECR (Full Access)
- ALB/ELB (Full Access)
- WAF (Full Access)

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd knowledge-database
```

### 2. Set Environment Variables
```bash
export AWS_REGION=us-west-2
export ENVIRONMENT=production  # or staging/dev
```

### 3. Run Deployment Script
```bash
./scripts/deploy-aws.sh production deploy
```

## Infrastructure Overview

### Architecture Components

#### Network Layer
- **VPC**: Multi-AZ setup with public, private, and database subnets
- **NAT Gateways**: One per AZ for high availability
- **VPC Endpoints**: For S3, ECR, CloudWatch, and Secrets Manager

#### Compute Layer
- **ECS Fargate**: Serverless container hosting
- **Auto Scaling**: CPU and memory-based scaling (3-20 tasks)
- **Application Load Balancer**: With WAF protection

#### Data Layer
- **RDS PostgreSQL**: With pgvector extension for embeddings
  - Multi-AZ deployment
  - Automated backups (30-day retention)
  - Read replica for production
- **Amazon OpenSearch**: For full-text search
  - 3-node cluster across AZs
  - Encrypted at rest and in transit
- **ElastiCache Redis**: For caching and sessions
  - Cluster mode with 3 nodes
  - Automatic failover

#### Storage & Secrets
- **S3**: For static assets and backups
- **Secrets Manager**: For database credentials and API keys
- **ECR**: For Docker image storage

## Deployment Steps

### 1. Initial Setup

#### Create ECR Repository
```bash
aws ecr create-repository --repository-name knowledge-database --region us-west-2
```

#### Build and Push Docker Image
```bash
# Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-west-2.amazonaws.com

# Build image
docker build -t knowledge-database:latest --target production .

# Tag image
docker tag knowledge-database:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-west-2.amazonaws.com/knowledge-database:production-latest

# Push image
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-west-2.amazonaws.com/knowledge-database:production-latest
```

### 2. Deploy Infrastructure with Terraform

#### Initialize Terraform
```bash
cd infrastructure/terraform/aws/environments/production

# Initialize backend
terraform init

# Review the plan
terraform plan

# Apply infrastructure
terraform apply
```

#### Key Terraform Commands
```bash
# Format code
terraform fmt -recursive

# Validate configuration
terraform validate

# Show current state
terraform show

# List resources
terraform state list

# Import existing resources
terraform import module.vpc.aws_vpc.main vpc-xxxxx
```

### 3. Database Setup

#### Run Migrations
```bash
# Connect to ECS task and run migrations
aws ecs run-task \
  --cluster knowledge-database-production \
  --task-definition knowledge-database-production \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}" \
  --overrides '{"containerOverrides":[{"name":"knowledge-database","command":["alembic","upgrade","head"]}]}'
```

#### Create pgvector Extension
```sql
-- Connect to RDS instance and run:
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Configure OpenSearch

The OpenSearch domain is automatically created with the following indexes:
- `knowledge_items`: Main content index
- `search_queries`: Query logging index
- `embeddings`: Vector similarity search

### 5. Verify Deployment

#### Check ECS Service Status
```bash
aws ecs describe-services \
  --cluster knowledge-database-production \
  --services knowledge-database-production
```

#### Test Health Endpoint
```bash
# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names knowledge-database-production-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Test health check
curl https://$ALB_DNS/health
```

## CI/CD Pipeline

### GitHub Actions Workflow

The deployment pipeline is triggered on:
- Push to `main` branch (staging deployment)
- Push to `production` branch (production deployment)
- Manual workflow dispatch

#### Pipeline Stages
1. **Code Quality**: Linting, type checking, security scanning
2. **Testing**: Unit tests with 85%+ coverage requirement
3. **Build**: Docker image creation and vulnerability scanning
4. **Deploy**: ECS service update with blue-green deployment
5. **Verify**: Health checks and smoke tests

### Setting up GitHub Secrets

Add these secrets to your GitHub repository:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
TF_STATE_BUCKET
TF_LOCK_TABLE
PRIVATE_SUBNET_IDS
ECS_SECURITY_GROUP_ID
SLACK_WEBHOOK (optional)
```

### Manual Deployment

```bash
# Deploy to staging
./scripts/deploy-aws.sh staging deploy

# Deploy to production
./scripts/deploy-aws.sh production deploy

# Update existing deployment
./scripts/deploy-aws.sh production update

# Check deployment status
./scripts/deploy-aws.sh production status
```

## Monitoring & Alerting

### CloudWatch Dashboards

Automatically created dashboards monitor:
- ECS task CPU/memory utilization
- Request count and latency
- Database connections and query performance
- Cache hit rates
- Error rates and logs

### Key Metrics to Monitor

#### Application Metrics
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active connections

#### Infrastructure Metrics
- ECS task count and health
- RDS CPU, memory, and connections
- OpenSearch cluster health and indexing rate
- Redis memory usage and evictions

### Alarms Configuration

Critical alarms are set for:
- High CPU utilization (>80%)
- High memory utilization (>80%)
- Database connection exhaustion (>90%)
- Disk space low (<10GB free)
- High error rate (>1%)
- Unhealthy targets in ALB

### Log Aggregation

All logs are sent to CloudWatch Logs with the following retention:
- Production: 90 days
- Staging: 30 days
- Development: 7 days

## Cost Optimization

### Estimated Monthly Costs (Production)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| ECS Fargate | 3 tasks (2vCPU, 4GB) | $150 |
| RDS PostgreSQL | db.r6g.xlarge, 200GB | $400 |
| OpenSearch | 3x r6g.xlarge.search | $600 |
| ElastiCache | 3x cache.r6g.xlarge | $450 |
| ALB | 1 load balancer | $25 |
| NAT Gateway | 3 gateways | $135 |
| S3 & Data Transfer | ~100GB | $50 |
| **Total** | | **~$1,810/month** |

### Cost Optimization Strategies

1. **Use Spot Instances**: Enable for non-production environments
2. **Reserved Instances**: Purchase 1-year RIs for 30% savings
3. **Auto Scaling**: Scale down during off-peak hours
4. **S3 Lifecycle Policies**: Move old data to Glacier
5. **VPC Endpoints**: Reduce NAT Gateway costs
6. **Right-sizing**: Monitor and adjust instance sizes

## Security Best Practices

### Network Security
- All databases in private subnets
- Security groups with least privilege
- VPC flow logs enabled
- WAF rules for common attacks

### Data Security
- Encryption at rest (KMS)
- Encryption in transit (TLS)
- Secrets in AWS Secrets Manager
- Regular automated backups

### Access Control
- IAM roles for service access
- No hardcoded credentials
- MFA for console access
- CloudTrail audit logging

### Compliance
- GDPR-ready infrastructure
- SOC2 compliance features
- HIPAA-eligible services

## Troubleshooting

### Common Issues and Solutions

#### ECS Tasks Failing to Start
```bash
# Check task stopped reason
aws ecs describe-tasks \
  --cluster knowledge-database-production \
  --tasks $(aws ecs list-tasks --cluster knowledge-database-production --query 'taskArns[0]' --output text)

# Check CloudWatch logs
aws logs tail /ecs/knowledge-database-production --follow
```

#### Database Connection Issues
```bash
# Test connectivity from ECS task
aws ecs execute-command \
  --cluster knowledge-database-production \
  --task <task-id> \
  --container knowledge-database \
  --interactive \
  --command "/bin/bash"

# Inside container
apt-get update && apt-get install -y postgresql-client
psql $DATABASE_URL
```

#### High Memory Usage
```bash
# Check memory metrics
aws cloudwatch get-metric-statistics \
  --namespace ECS/ContainerInsights \
  --metric-name MemoryUtilized \
  --dimensions Name=ServiceName,Value=knowledge-database-production \
  --statistics Average \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600
```

## Rollback Procedures

### Automatic Rollback
The ECS service has circuit breaker enabled and will automatically rollback failed deployments.

### Manual Rollback

#### Quick Rollback (Previous Version)
```bash
./scripts/deploy-aws.sh production rollback
```

#### Rollback to Specific Version
```bash
# List available task definition revisions
aws ecs list-task-definitions --family knowledge-database-production

# Update service with specific revision
aws ecs update-service \
  --cluster knowledge-database-production \
  --service knowledge-database-production \
  --task-definition knowledge-database-production:10
```

#### Database Rollback
```bash
# Connect to database
psql $DATABASE_URL

# Rollback migration
alembic downgrade -1
```

### Disaster Recovery

#### Backup Strategy
- RDS: Automated daily backups (30-day retention)
- OpenSearch: Daily snapshots to S3
- Application data: S3 versioning enabled

#### Recovery Time Objectives
- RTO (Recovery Time Objective): 1 hour
- RPO (Recovery Point Objective): 24 hours

#### Restore Procedures
```bash
# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier knowledge-database-production-restored \
  --db-snapshot-identifier <snapshot-id>

# Restore OpenSearch from snapshot
aws opensearch restore-domain-from-snapshot \
  --domain-name knowledge-database-production-restored \
  --snapshot-name <snapshot-name>
```

## Support and Maintenance

### Regular Maintenance Tasks

#### Weekly
- Review CloudWatch metrics and alarms
- Check for security updates
- Review error logs

#### Monthly
- Update dependencies
- Performance review
- Cost optimization review
- Security audit

#### Quarterly
- Disaster recovery drill
- Load testing
- Infrastructure review
- Documentation update

### Getting Help

For issues or questions:
1. Check CloudWatch logs and metrics
2. Review this documentation
3. Check AWS service health dashboard
4. Contact DevOps team

## Appendix

### Environment Variables

Required environment variables for the application:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379
OPENSEARCH_URL=https://host:443
JWT_SECRET=<secret>
SECRET_KEY=<secret>
APP_ENV=production
LOG_LEVEL=INFO
```

### Useful AWS CLI Commands

```bash
# List all resources in a stack
aws cloudformation list-stack-resources --stack-name knowledge-database-production

# Get secret value
aws secretsmanager get-secret-value --secret-id knowledge-database-production-database-url

# Tail logs
aws logs tail /ecs/knowledge-database-production --follow

# Get metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=knowledge-database-production \
  --statistics Average \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600
```

### Terraform State Management

```bash
# Backup state
terraform state pull > terraform.tfstate.backup

# Import existing resource
terraform import aws_instance.example i-1234567890abcdef0

# Remove resource from state
terraform state rm aws_instance.example

# Move resource
terraform state mv aws_instance.example aws_instance.new_name
```

---

This deployment is production-ready and follows AWS best practices for security, scalability, and reliability. For additional support or customization, please refer to the AWS documentation or contact your DevOps team.