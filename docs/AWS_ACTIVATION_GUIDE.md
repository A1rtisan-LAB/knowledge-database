# AWS Deployment Activation Guide

## 📚 Overview

This guide explains how to activate AWS deployment workflows for the Knowledge Database project. The AWS deployment features are currently disabled to allow for local development and testing without requiring AWS credentials.

---

## 🚀 Quick Start

### Step 1: Enable Workflows
```bash
# Navigate to workflows directory
cd .github/workflows/

# Remove .disabled extension from AWS workflows
mv deploy.yml.disabled deploy.yml
mv deploy-aws.yml.disabled deploy-aws.yml

# Commit and push changes
git add .
git commit -m "ci: enable AWS deployment workflows"
git push
```

### Step 2: Configure GitHub Secrets
Add the following secrets in your repository settings:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

That's it for basic activation! Continue reading for detailed setup.

---

## 📋 Prerequisites

### 1. AWS Account Setup
- Active AWS account with billing configured
- Basic understanding of AWS services (ECS, RDS, S3)
- Estimated cost: ~$1,810/month for production

### 2. Required Tools
- AWS CLI v2.x
- Terraform >= 1.5.0
- Docker >= 20.x

### 3. Local Environment
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS CLI
aws configure
```

---

## 🔐 GitHub Secrets Configuration

### Required Secrets

Navigate to: **Settings → Secrets and variables → Actions**

#### 1. AWS Credentials (Required)
| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `AWS_ACCESS_KEY_ID` | AWS access key identifier | IAM → Users → Security credentials → Create access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | Generated with access key ID |

#### 2. Infrastructure Secrets (Required for Terraform)
| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `TF_STATE_BUCKET` | S3 bucket for Terraform state | `my-terraform-state-bucket` |
| `TF_LOCK_TABLE` | DynamoDB table for state locking | `terraform-state-lock` |

#### 3. Network Configuration (Required for ECS)
| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `PRIVATE_SUBNET_IDS` | Private subnet IDs (comma-separated) | `subnet-abc123,subnet-def456` |
| `ECS_SECURITY_GROUP_ID` | Security group for ECS tasks | `sg-abc12345` |

#### 4. Optional Secrets
| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `SLACK_WEBHOOK` | Slack notifications | `https://hooks.slack.com/...` |
| `AWS_ROLE_ARN` | For OIDC authentication | `arn:aws:iam::123456789012:role/...` |

---

## 🏗️ AWS Infrastructure Setup

### Step 1: Create IAM User

```bash
# Create IAM user with programmatic access
aws iam create-user --user-name github-actions-user

# Attach administrator policy (or custom policy)
aws iam attach-user-policy \
  --user-name github-actions-user \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# Create access key
aws iam create-access-key --user-name github-actions-user
```

### Step 2: Create S3 Bucket for Terraform State

```bash
# Create S3 bucket
aws s3 mb s3://knowledge-db-terraform-state-$(date +%s)

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket knowledge-db-terraform-state-$(date +%s) \
  --versioning-configuration Status=Enabled
```

### Step 3: Create DynamoDB Table for State Locking

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Step 4: Deploy Infrastructure with Terraform

```bash
# Navigate to Terraform directory
cd infrastructure/terraform/aws

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply infrastructure
terraform apply
```

---

## 🔄 Workflow Activation

### Available Workflows

#### 1. `deploy.yml` - Main CI/CD Pipeline
- **Triggers**: Push to main/production branches
- **Features**: Code quality, testing, Docker build, ECS deployment
- **Required Secrets**: All AWS and infrastructure secrets

#### 2. `deploy-aws.yml` - Tag-based Deployment
- **Triggers**: Version tags (v*)
- **Features**: Production deployment with release creation
- **Region**: ap-northeast-2 (Seoul)

### Activation Steps

1. **Remove .disabled extension**:
   ```bash
   mv deploy.yml.disabled deploy.yml
   ```

2. **Verify workflow syntax**:
   ```bash
   # Install act for local testing (optional)
   brew install act
   act -l
   ```

3. **Test with manual trigger**:
   - Go to Actions tab in GitHub
   - Select workflow
   - Click "Run workflow"

---

## 🧪 Testing Your Setup

### 1. Validate AWS Credentials
```bash
aws sts get-caller-identity
```

### 2. Test GitHub Secrets
Create a test workflow (`.github/workflows/test-secrets.yml`):
```yaml
name: Test AWS Secrets
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Check AWS credentials
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          if [ -n "$AWS_ACCESS_KEY_ID" ]; then
            echo "✅ AWS credentials are configured"
          else
            echo "❌ AWS credentials are missing"
          fi
```

### 3. Verify Infrastructure
```bash
# Check ECS cluster
aws ecs list-clusters

# Check RDS instances
aws rds describe-db-instances

# Check S3 buckets
aws s3 ls
```

---

## 💰 Cost Estimation

### Monthly Costs (Production)
| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| ECS Fargate | 3 tasks (2vCPU, 4GB) | $300 |
| RDS PostgreSQL | db.r6g.xlarge | $400 |
| OpenSearch | 3-node cluster | $600 |
| ElastiCache | Redis cluster | $350 |
| Load Balancer | Application LB | $50 |
| Others | S3, CloudWatch, NAT | $110 |
| **Total** | | **~$1,810/month** |

### Cost Optimization Tips
- Use spot instances for non-production
- Enable auto-scaling based on usage
- Use reserved instances for predictable workloads
- Implement S3 lifecycle policies

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Workflow Not Triggering
- Check if file has `.disabled` extension
- Verify branch protection rules
- Check workflow syntax with `act`

#### 2. AWS Authentication Failed
```yaml
Error: Could not assume role
```
**Solution**: Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are correctly set

#### 3. Terraform State Lock Error
```
Error acquiring the state lock
```
**Solution**: 
```bash
# Force unlock (use with caution)
terraform force-unlock <lock-id>
```

#### 4. ECS Task Failed to Start
- Check CloudWatch logs
- Verify security group rules
- Ensure Docker image exists in ECR

---

## 📚 Additional Resources

### Documentation
- [AWS Deployment Guide](./AWS_DEPLOYMENT_GUIDE.md)
- [CI/CD Pipeline Documentation](./CI_CD_PIPELINE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

### AWS Documentation
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [RDS with PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)

---

## 🤝 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review GitHub Actions logs
3. Create an issue in the repository
4. Contact the development team

---

## ✅ Checklist

Before activating AWS deployment:
- [ ] AWS account is active
- [ ] IAM user created with necessary permissions
- [ ] GitHub Secrets configured
- [ ] Terraform state bucket created
- [ ] DynamoDB lock table created
- [ ] Workflows enabled (removed .disabled)
- [ ] Test deployment successful

---

*Last updated: 2025-08-21*