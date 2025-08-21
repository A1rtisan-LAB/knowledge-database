#!/bin/bash

# AWS Deployment Script for Knowledge Database
# Usage: ./deploy-aws.sh [environment] [action]
# Environments: dev, staging, production
# Actions: deploy, update, rollback, status

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
ACTION=${2:-deploy}
AWS_REGION=${AWS_REGION:-us-west-2}
PROJECT_NAME="knowledge-database"
TERRAFORM_DIR="../infrastructure/terraform/aws"
ENVIRONMENTS_DIR="$TERRAFORM_DIR/environments"

# Logging
LOG_FILE="/tmp/${PROJECT_NAME}-deploy-$(date +%Y%m%d-%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Knowledge Database AWS Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Action: $ACTION"
echo "Region: $AWS_REGION"
echo "Log file: $LOG_FILE"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed${NC}"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}Terraform is not installed${NC}"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}AWS credentials not configured${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}All prerequisites met${NC}"
}

# Function to validate environment
validate_environment() {
    case $ENVIRONMENT in
        dev|staging|production)
            echo -e "${GREEN}Environment '$ENVIRONMENT' is valid${NC}"
            ;;
        *)
            echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
            echo "Valid environments: dev, staging, production"
            exit 1
            ;;
    esac
}

# Function to get AWS account ID
get_aws_account_id() {
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo "AWS Account ID: $AWS_ACCOUNT_ID"
}

# Function to create ECR repository if it doesn't exist
create_ecr_repository() {
    echo -e "${YELLOW}Checking ECR repository...${NC}"
    
    REPO_NAME="${PROJECT_NAME}"
    
    if aws ecr describe-repositories --repository-names $REPO_NAME --region $AWS_REGION &> /dev/null; then
        echo "ECR repository already exists"
    else
        echo "Creating ECR repository..."
        aws ecr create-repository \
            --repository-name $REPO_NAME \
            --region $AWS_REGION \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256
        
        # Set lifecycle policy
        aws ecr put-lifecycle-policy \
            --repository-name $REPO_NAME \
            --lifecycle-policy-text '{
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep last 10 images",
                        "selection": {
                            "tagStatus": "any",
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            }'
        
        echo -e "${GREEN}ECR repository created${NC}"
    fi
    
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO_NAME"
    echo "ECR URI: $ECR_URI"
}

# Function to build and push Docker image
build_and_push_image() {
    echo -e "${YELLOW}Building Docker image...${NC}"
    
    # Get git commit hash for tagging
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
    IMAGE_TAG="${ENVIRONMENT}-${GIT_COMMIT}-$(date +%Y%m%d-%H%M%S)"
    
    # Login to ECR
    echo "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
    
    # Build image
    echo "Building Docker image..."
    docker build \
        --target production \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VCS_REF=$GIT_COMMIT \
        --build-arg VERSION=$IMAGE_TAG \
        -t $ECR_URI:$IMAGE_TAG \
        -t $ECR_URI:$ENVIRONMENT-latest \
        ..
    
    # Push image
    echo "Pushing Docker image..."
    docker push $ECR_URI:$IMAGE_TAG
    docker push $ECR_URI:$ENVIRONMENT-latest
    
    echo -e "${GREEN}Docker image pushed: $ECR_URI:$IMAGE_TAG${NC}"
    
    # Export for use in Terraform
    export TF_VAR_image_tag=$IMAGE_TAG
}

# Function to initialize Terraform backend
init_terraform_backend() {
    echo -e "${YELLOW}Initializing Terraform backend...${NC}"
    
    # Create S3 bucket for state if it doesn't exist
    STATE_BUCKET="${PROJECT_NAME}-terraform-state-${AWS_ACCOUNT_ID}"
    LOCK_TABLE="${PROJECT_NAME}-terraform-locks"
    
    if ! aws s3api head-bucket --bucket $STATE_BUCKET 2>/dev/null; then
        echo "Creating S3 bucket for Terraform state..."
        aws s3api create-bucket \
            --bucket $STATE_BUCKET \
            --region $AWS_REGION \
            --create-bucket-configuration LocationConstraint=$AWS_REGION
        
        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket $STATE_BUCKET \
            --versioning-configuration Status=Enabled
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket $STATE_BUCKET \
            --server-side-encryption-configuration '{
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }'
    fi
    
    # Create DynamoDB table for state locking if it doesn't exist
    if ! aws dynamodb describe-table --table-name $LOCK_TABLE &> /dev/null; then
        echo "Creating DynamoDB table for state locking..."
        aws dynamodb create-table \
            --table-name $LOCK_TABLE \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
            --region $AWS_REGION
        
        # Wait for table to be active
        aws dynamodb wait table-exists --table-name $LOCK_TABLE
    fi
    
    echo -e "${GREEN}Terraform backend initialized${NC}"
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    echo -e "${YELLOW}Deploying infrastructure with Terraform...${NC}"
    
    cd "$ENVIRONMENTS_DIR/$ENVIRONMENT"
    
    # Initialize Terraform
    terraform init \
        -backend-config="bucket=$STATE_BUCKET" \
        -backend-config="key=$ENVIRONMENT/terraform.tfstate" \
        -backend-config="region=$AWS_REGION" \
        -backend-config="dynamodb_table=$LOCK_TABLE"
    
    # Plan deployment
    echo "Planning Terraform deployment..."
    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -var="ecr_repository_url=$ECR_URI" \
        -var="image_tag=${TF_VAR_image_tag:-$ENVIRONMENT-latest}" \
        -out=tfplan
    
    # Apply deployment
    read -p "Do you want to apply this plan? (yes/no): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        terraform apply tfplan
        echo -e "${GREEN}Infrastructure deployed successfully${NC}"
    else
        echo -e "${YELLOW}Deployment cancelled${NC}"
        exit 0
    fi
    
    cd -
}

# Function to update ECS service
update_ecs_service() {
    echo -e "${YELLOW}Updating ECS service...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Force new deployment
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION
    
    echo "Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION
    
    echo -e "${GREEN}ECS service updated successfully${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    TASK_DEFINITION="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get subnet and security group IDs from Terraform output
    cd "$ENVIRONMENTS_DIR/$ENVIRONMENT"
    SUBNET_IDS=$(terraform output -json private_subnet_ids | jq -r '.[]' | paste -sd "," -)
    SECURITY_GROUP_ID=$(terraform output -raw ecs_security_group_id)
    cd -
    
    # Run migration task
    TASK_ARN=$(aws ecs run-task \
        --cluster $CLUSTER_NAME \
        --task-definition $TASK_DEFINITION \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=DISABLED}" \
        --overrides '{"containerOverrides":[{"name":"'$PROJECT_NAME'","command":["alembic","upgrade","head"]}]}' \
        --region $AWS_REGION \
        --query 'tasks[0].taskArn' \
        --output text)
    
    echo "Migration task started: $TASK_ARN"
    
    # Wait for task to complete
    aws ecs wait tasks-stopped \
        --cluster $CLUSTER_NAME \
        --tasks $TASK_ARN \
        --region $AWS_REGION
    
    # Check exit code
    EXIT_CODE=$(aws ecs describe-tasks \
        --cluster $CLUSTER_NAME \
        --tasks $TASK_ARN \
        --region $AWS_REGION \
        --query 'tasks[0].containers[0].exitCode' \
        --output text)
    
    if [ "$EXIT_CODE" = "0" ]; then
        echo -e "${GREEN}Migrations completed successfully${NC}"
    else
        echo -e "${RED}Migrations failed with exit code $EXIT_CODE${NC}"
        exit 1
    fi
}

# Function to get deployment status
get_deployment_status() {
    echo -e "${YELLOW}Getting deployment status...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get service status
    aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount,PendingCount:pendingCount}' \
        --output table
    
    # Get task status
    echo ""
    echo "Running tasks:"
    aws ecs list-tasks \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'taskArns' \
        --output table
    
    # Get ALB URL
    cd "$ENVIRONMENTS_DIR/$ENVIRONMENT"
    ALB_URL=$(terraform output -raw alb_dns_name 2>/dev/null || echo "Not available")
    cd -
    
    echo ""
    echo -e "${GREEN}Application URL: https://$ALB_URL${NC}"
    
    # Health check
    if [ "$ALB_URL" != "Not available" ]; then
        echo ""
        echo "Health check:"
        curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "https://$ALB_URL/health" || true
    fi
}

# Function to rollback deployment
rollback_deployment() {
    echo -e "${YELLOW}Rolling back deployment...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    TASK_DEFINITION="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get previous task definition revision
    CURRENT_REVISION=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].taskDefinition' \
        --output text | awk -F: '{print $NF}')
    
    PREVIOUS_REVISION=$((CURRENT_REVISION - 1))
    
    if [ $PREVIOUS_REVISION -lt 1 ]; then
        echo -e "${RED}No previous revision to rollback to${NC}"
        exit 1
    fi
    
    echo "Rolling back from revision $CURRENT_REVISION to $PREVIOUS_REVISION"
    
    # Update service with previous task definition
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition "${TASK_DEFINITION}:${PREVIOUS_REVISION}" \
        --region $AWS_REGION
    
    # Wait for rollback to complete
    echo "Waiting for rollback to complete..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION
    
    echo -e "${GREEN}Rollback completed successfully${NC}"
}

# Function to destroy infrastructure
destroy_infrastructure() {
    echo -e "${RED}WARNING: This will destroy all infrastructure for environment: $ENVIRONMENT${NC}"
    read -p "Are you sure? Type 'yes' to confirm: " -r
    if [[ $REPLY != "yes" ]]; then
        echo "Destroy cancelled"
        exit 0
    fi
    
    cd "$ENVIRONMENTS_DIR/$ENVIRONMENT"
    
    terraform destroy \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -var="ecr_repository_url=$ECR_URI" \
        -var="image_tag=latest" \
        -auto-approve
    
    cd -
    
    echo -e "${GREEN}Infrastructure destroyed${NC}"
}

# Main execution
main() {
    check_prerequisites
    validate_environment
    get_aws_account_id
    
    case $ACTION in
        deploy)
            create_ecr_repository
            build_and_push_image
            init_terraform_backend
            deploy_infrastructure
            run_migrations
            get_deployment_status
            ;;
        update)
            create_ecr_repository
            build_and_push_image
            update_ecs_service
            get_deployment_status
            ;;
        rollback)
            rollback_deployment
            get_deployment_status
            ;;
        status)
            get_deployment_status
            ;;
        destroy)
            destroy_infrastructure
            ;;
        *)
            echo -e "${RED}Invalid action: $ACTION${NC}"
            echo "Valid actions: deploy, update, rollback, status, destroy"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed successfully${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Run main function
main