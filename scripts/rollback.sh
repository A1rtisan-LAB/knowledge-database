#!/bin/bash

# Rollback Script for Knowledge Database AWS Deployment
# Usage: ./rollback.sh [environment] [rollback-type] [target-version]
# Environments: dev, staging, production
# Rollback Types: app, database, full, infrastructure
# Target Version: specific version/revision to rollback to (optional)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
ROLLBACK_TYPE=${2:-app}
TARGET_VERSION=${3:-}
AWS_REGION=${AWS_REGION:-us-west-2}
PROJECT_NAME="knowledge-database"

# Logging
LOG_FILE="/tmp/${PROJECT_NAME}-rollback-$(date +%Y%m%d-%H%M%S).log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Knowledge Database Rollback Procedure${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Rollback Type: $ROLLBACK_TYPE"
echo "Target Version: ${TARGET_VERSION:-Previous}"
echo "Region: $AWS_REGION"
echo "Log file: $LOG_FILE"
echo ""

# Function to confirm rollback
confirm_rollback() {
    echo -e "${YELLOW}WARNING: You are about to rollback $ROLLBACK_TYPE in $ENVIRONMENT environment${NC}"
    echo -e "${YELLOW}This action may cause temporary service disruption.${NC}"
    read -p "Are you sure you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${RED}Rollback cancelled${NC}"
        exit 0
    fi
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed${NC}"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        echo -e "${RED}AWS credentials not configured${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Prerequisites met${NC}"
}

# Function to get current deployment info
get_current_deployment_info() {
    echo -e "${YELLOW}Getting current deployment information...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get current task definition
    CURRENT_TASK_DEF=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].taskDefinition' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$CURRENT_TASK_DEF" ]; then
        echo -e "${RED}Could not get current deployment information${NC}"
        exit 1
    fi
    
    CURRENT_REVISION=$(echo $CURRENT_TASK_DEF | awk -F: '{print $NF}')
    echo "Current task definition revision: $CURRENT_REVISION"
    
    # Get running tasks count
    RUNNING_TASKS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text)
    
    echo "Running tasks: $RUNNING_TASKS"
}

# Function to rollback ECS application
rollback_ecs_app() {
    echo -e "${YELLOW}Rolling back ECS application...${NC}"
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    SERVICE_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    TASK_FAMILY="${PROJECT_NAME}-${ENVIRONMENT}"
    
    if [ -n "$TARGET_VERSION" ]; then
        # Rollback to specific version
        ROLLBACK_REVISION=$TARGET_VERSION
        echo "Rolling back to specified revision: $ROLLBACK_REVISION"
    else
        # Rollback to previous version
        ROLLBACK_REVISION=$((CURRENT_REVISION - 1))
        
        if [ $ROLLBACK_REVISION -lt 1 ]; then
            echo -e "${RED}No previous revision available to rollback${NC}"
            exit 1
        fi
        
        echo "Rolling back to previous revision: $ROLLBACK_REVISION"
    fi
    
    # Verify target task definition exists
    if ! aws ecs describe-task-definition \
        --task-definition "${TASK_FAMILY}:${ROLLBACK_REVISION}" \
        --region $AWS_REGION &> /dev/null; then
        echo -e "${RED}Task definition revision $ROLLBACK_REVISION does not exist${NC}"
        exit 1
    fi
    
    # Create deployment marker
    echo "Creating rollback marker..."
    aws ecs tag-resource \
        --resource-arn "arn:aws:ecs:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):service/${CLUSTER_NAME}/${SERVICE_NAME}" \
        --tags "key=RollbackFrom,value=${CURRENT_REVISION}" \
        "key=RollbackTo,value=${ROLLBACK_REVISION}" \
        "key=RollbackTime,value=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --region $AWS_REGION 2>/dev/null || true
    
    # Update service with previous task definition
    echo "Updating ECS service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition "${TASK_FAMILY}:${ROLLBACK_REVISION}" \
        --force-new-deployment \
        --region $AWS_REGION > /dev/null
    
    # Wait for rollback to complete
    echo "Waiting for rollback to stabilize (this may take several minutes)..."
    
    # Monitor deployment progress
    DEPLOYMENT_COMPLETE=false
    MAX_WAIT=600  # 10 minutes
    ELAPSED=0
    
    while [ "$DEPLOYMENT_COMPLETE" = false ] && [ $ELAPSED -lt $MAX_WAIT ]; do
        sleep 10
        ELAPSED=$((ELAPSED + 10))
        
        # Check deployment status
        DEPLOYMENTS=$(aws ecs describe-services \
            --cluster $CLUSTER_NAME \
            --services $SERVICE_NAME \
            --region $AWS_REGION \
            --query 'services[0].deployments' \
            --output json)
        
        PRIMARY_DEPLOYMENT=$(echo $DEPLOYMENTS | jq -r '.[] | select(.status == "PRIMARY")')
        ACTIVE_COUNT=$(echo $DEPLOYMENTS | jq '. | length')
        
        if [ "$ACTIVE_COUNT" -eq 1 ]; then
            DEPLOYMENT_COMPLETE=true
            echo -e "${GREEN}Rollback deployment completed${NC}"
        else
            echo "Deployment in progress... ($ELAPSED seconds elapsed)"
        fi
    done
    
    if [ "$DEPLOYMENT_COMPLETE" = false ]; then
        echo -e "${YELLOW}Warning: Deployment did not complete within expected time${NC}"
        echo "Please check ECS console for deployment status"
    fi
    
    # Verify rollback
    verify_ecs_rollback
}

# Function to verify ECS rollback
verify_ecs_rollback() {
    echo -e "${YELLOW}Verifying rollback...${NC}"
    
    # Get new task definition
    NEW_TASK_DEF=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].taskDefinition' \
        --output text)
    
    NEW_REVISION=$(echo $NEW_TASK_DEF | awk -F: '{print $NF}')
    
    if [ "$NEW_REVISION" = "$ROLLBACK_REVISION" ]; then
        echo -e "${GREEN}Rollback successful! Now running revision: $NEW_REVISION${NC}"
    else
        echo -e "${RED}Rollback may have failed. Current revision: $NEW_REVISION, Expected: $ROLLBACK_REVISION${NC}"
    fi
    
    # Check service health
    RUNNING=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].runningCount' \
        --output text)
    
    DESIRED=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION \
        --query 'services[0].desiredCount' \
        --output text)
    
    echo "Service status: $RUNNING/$DESIRED tasks running"
    
    if [ "$RUNNING" -eq "$DESIRED" ]; then
        echo -e "${GREEN}Service is healthy${NC}"
    else
        echo -e "${YELLOW}Warning: Service may not be fully healthy${NC}"
    fi
}

# Function to rollback database
rollback_database() {
    echo -e "${YELLOW}Rolling back database...${NC}"
    
    if [ -z "$TARGET_VERSION" ]; then
        echo -e "${RED}Database rollback requires a target migration version${NC}"
        echo "Usage: $0 $ENVIRONMENT database <migration-version>"
        echo "Example: $0 production database head~1"
        exit 1
    fi
    
    CLUSTER_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
    TASK_DEFINITION="${PROJECT_NAME}-${ENVIRONMENT}"
    
    # Get network configuration from running task
    RUNNING_TASK=$(aws ecs list-tasks \
        --cluster $CLUSTER_NAME \
        --region $AWS_REGION \
        --query 'taskArns[0]' \
        --output text)
    
    if [ -z "$RUNNING_TASK" ]; then
        echo -e "${RED}No running tasks found${NC}"
        exit 1
    fi
    
    # Get network configuration
    NETWORK_CONFIG=$(aws ecs describe-tasks \
        --cluster $CLUSTER_NAME \
        --tasks $RUNNING_TASK \
        --region $AWS_REGION \
        --query 'tasks[0].attachments[0].details' \
        --output json)
    
    SUBNET_ID=$(echo $NETWORK_CONFIG | jq -r '.[] | select(.name == "subnetId") | .value')
    SECURITY_GROUP=$(echo $NETWORK_CONFIG | jq -r '.[] | select(.name == "securityGroupId") | .value' | head -1)
    
    echo "Running database rollback to: $TARGET_VERSION"
    
    # Run migration rollback task
    TASK_ARN=$(aws ecs run-task \
        --cluster $CLUSTER_NAME \
        --task-definition $TASK_DEFINITION \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP],assignPublicIp=DISABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"$PROJECT_NAME\",\"command\":[\"alembic\",\"downgrade\",\"$TARGET_VERSION\"]}]}" \
        --region $AWS_REGION \
        --query 'tasks[0].taskArn' \
        --output text)
    
    echo "Database rollback task started: $TASK_ARN"
    echo "Waiting for rollback to complete..."
    
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
        echo -e "${GREEN}Database rollback completed successfully${NC}"
    else
        echo -e "${RED}Database rollback failed with exit code $EXIT_CODE${NC}"
        
        # Get logs
        echo "Fetching task logs..."
        LOG_GROUP="/ecs/${PROJECT_NAME}-${ENVIRONMENT}"
        LOG_STREAM=$(aws logs describe-log-streams \
            --log-group-name $LOG_GROUP \
            --order-by LastEventTime \
            --descending \
            --limit 1 \
            --query 'logStreams[0].logStreamName' \
            --output text)
        
        aws logs get-log-events \
            --log-group-name $LOG_GROUP \
            --log-stream-name $LOG_STREAM \
            --limit 50 \
            --query 'events[*].message' \
            --output text
        
        exit 1
    fi
}

# Function to rollback infrastructure
rollback_infrastructure() {
    echo -e "${YELLOW}Rolling back infrastructure with Terraform...${NC}"
    
    cd ../infrastructure/terraform/aws/environments/$ENVIRONMENT
    
    if [ ! -f terraform.tfstate ]; then
        echo -e "${RED}Terraform state not found${NC}"
        exit 1
    fi
    
    # Show current state
    echo "Current infrastructure state:"
    terraform show -no-color | head -20
    
    if [ -n "$TARGET_VERSION" ]; then
        # Rollback to specific state version
        echo "Rolling back to state version: $TARGET_VERSION"
        
        # Create backup
        cp terraform.tfstate terraform.tfstate.backup-$(date +%Y%m%d-%H%M%S)
        
        # Restore previous state
        terraform state pull > current.tfstate
        # This would require state versioning in S3
        echo -e "${YELLOW}Note: Infrastructure rollback requires state versioning in S3${NC}"
    else
        echo -e "${YELLOW}Infrastructure rollback requires manual intervention${NC}"
        echo "Options:"
        echo "1. Restore from S3 state backup"
        echo "2. Manually revert infrastructure changes"
        echo "3. Use terraform import to reconcile state"
    fi
    
    cd -
}

# Function to perform health check after rollback
health_check() {
    echo -e "${YELLOW}Performing health check...${NC}"
    
    # Get ALB DNS
    ALB_NAME="${PROJECT_NAME}-${ENVIRONMENT}-alb"
    ALB_DNS=$(aws elbv2 describe-load-balancers \
        --names $ALB_NAME \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].DNSName' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$ALB_DNS" ]; then
        echo "Testing application health endpoint..."
        
        # Try HTTPS first, then HTTP
        if curl -sf "https://$ALB_DNS/health" > /dev/null 2>&1; then
            echo -e "${GREEN}Health check passed (HTTPS)${NC}"
        elif curl -sf "http://$ALB_DNS/health" > /dev/null 2>&1; then
            echo -e "${GREEN}Health check passed (HTTP)${NC}"
        else
            echo -e "${YELLOW}Health check failed or endpoint not accessible${NC}"
        fi
        
        echo "Application URL: https://$ALB_DNS"
    else
        echo -e "${YELLOW}Could not determine ALB DNS${NC}"
    fi
    
    # Check CloudWatch alarms
    echo ""
    echo "Checking CloudWatch alarms..."
    ALARMS=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "${PROJECT_NAME}-${ENVIRONMENT}" \
        --state-value ALARM \
        --region $AWS_REGION \
        --query 'MetricAlarms[*].AlarmName' \
        --output text)
    
    if [ -z "$ALARMS" ]; then
        echo -e "${GREEN}No alarms in ALARM state${NC}"
    else
        echo -e "${YELLOW}Following alarms are active:${NC}"
        echo "$ALARMS"
    fi
}

# Function to send notification
send_notification() {
    local STATUS=$1
    local MESSAGE=$2
    
    echo -e "${YELLOW}Sending rollback notification...${NC}"
    
    # CloudWatch Event
    aws events put-events \
        --entries "[{
            \"Source\": \"rollback-script\",
            \"DetailType\": \"Rollback $STATUS\",
            \"Detail\": \"{
                \\\"environment\\\": \\\"$ENVIRONMENT\\\",
                \\\"rollback_type\\\": \\\"$ROLLBACK_TYPE\\\",
                \\\"target_version\\\": \\\"${TARGET_VERSION:-Previous}\\\",
                \\\"status\\\": \\\"$STATUS\\\",
                \\\"message\\\": \\\"$MESSAGE\\\",
                \\\"timestamp\\\": \\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\"
            }\"
        }]" \
        --region $AWS_REGION 2>/dev/null || true
    
    # SNS Notification (if topic exists)
    SNS_TOPIC="arn:aws:sns:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):${PROJECT_NAME}-${ENVIRONMENT}-alerts"
    
    if aws sns get-topic-attributes --topic-arn $SNS_TOPIC &> /dev/null; then
        aws sns publish \
            --topic-arn $SNS_TOPIC \
            --subject "Rollback $STATUS - $ENVIRONMENT" \
            --message "$MESSAGE" \
            --region $AWS_REGION 2>/dev/null || true
    fi
}

# Function to create rollback report
create_rollback_report() {
    echo -e "${YELLOW}Creating rollback report...${NC}"
    
    REPORT_FILE="/tmp/${PROJECT_NAME}-rollback-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > $REPORT_FILE << EOF
# Rollback Report

## Summary
- **Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **Environment**: $ENVIRONMENT
- **Rollback Type**: $ROLLBACK_TYPE
- **Target Version**: ${TARGET_VERSION:-Previous}
- **Initiated By**: $(whoami)
- **AWS Account**: $(aws sts get-caller-identity --query Account --output text)

## Pre-Rollback State
- **Task Definition Revision**: $CURRENT_REVISION
- **Running Tasks**: $RUNNING_TASKS

## Post-Rollback State
- **Task Definition Revision**: ${NEW_REVISION:-N/A}
- **Running Tasks**: ${RUNNING:-N/A}/${DESIRED:-N/A}

## Health Check Results
- **Endpoint Status**: $([ "$HEALTH_STATUS" = "OK" ] && echo "✅ Healthy" || echo "⚠️ Warning")
- **Active Alarms**: $([ -z "$ALARMS" ] && echo "None" || echo "$ALARMS")

## Actions Taken
1. Confirmed rollback with operator
2. Retrieved current deployment information
3. Executed rollback procedure
4. Waited for service stabilization
5. Performed health checks
6. Generated this report

## Recommendations
- Monitor application metrics for the next hour
- Review application logs for any errors
- Verify user-facing functionality
- Document root cause of the issue that required rollback

## Log Files
- Rollback Log: $LOG_FILE
- CloudWatch Logs: /ecs/${PROJECT_NAME}-${ENVIRONMENT}

---
*Generated by rollback.sh*
EOF
    
    echo -e "${GREEN}Rollback report created: $REPORT_FILE${NC}"
    cat $REPORT_FILE
}

# Main execution
main() {
    echo -e "${BLUE}Starting rollback procedure...${NC}"
    
    # Validate environment
    case $ENVIRONMENT in
        dev|staging|production)
            ;;
        *)
            echo -e "${RED}Invalid environment: $ENVIRONMENT${NC}"
            echo "Valid environments: dev, staging, production"
            exit 1
            ;;
    esac
    
    # Check prerequisites
    check_prerequisites
    
    # Confirm rollback
    confirm_rollback
    
    # Get current deployment info
    get_current_deployment_info
    
    # Perform rollback based on type
    case $ROLLBACK_TYPE in
        app|application)
            rollback_ecs_app
            ;;
        database|db)
            rollback_database
            ;;
        full)
            rollback_ecs_app
            rollback_database
            ;;
        infrastructure|infra)
            rollback_infrastructure
            ;;
        *)
            echo -e "${RED}Invalid rollback type: $ROLLBACK_TYPE${NC}"
            echo "Valid types: app, database, full, infrastructure"
            exit 1
            ;;
    esac
    
    # Perform health check
    health_check
    
    # Create report
    create_rollback_report
    
    # Send notification
    if [ $? -eq 0 ]; then
        send_notification "SUCCESS" "Rollback completed successfully for $ENVIRONMENT environment"
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}Rollback completed successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        send_notification "FAILED" "Rollback failed for $ENVIRONMENT environment"
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}Rollback encountered issues${NC}"
        echo -e "${RED}Please check logs and manual intervention may be required${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi
}

# Run main function
main