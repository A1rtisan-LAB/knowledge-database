#!/bin/bash
# Local Deployment Script for Knowledge Database
# Optimized for M1 Mac

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Knowledge Database Local Deployment${NC}"
echo "=========================================="

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}❌ .env.production not found!${NC}"
    echo "Creating from template..."
    cp .env.template .env.production
    echo -e "${YELLOW}⚠️  Please update .env.production with your settings${NC}"
    exit 1
fi

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs)

# Function to check if service is running
check_service() {
    if docker ps | grep -q $1; then
        echo -e "${GREEN}✅ $1 is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 is not running${NC}"
        return 1
    fi
}

# 1. Build Docker image
echo -e "\n${YELLOW}📦 Building Docker image...${NC}"
docker build -f Dockerfile.prod -t knowledge-database:latest .

# 2. Stop existing containers
echo -e "\n${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# 3. Start services
echo -e "\n${YELLOW}🚀 Starting services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# 4. Wait for services to be healthy
echo -e "\n${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# 5. Check service status
echo -e "\n${YELLOW}🔍 Checking service status...${NC}"
check_service "kb-postgres-prod"
check_service "kb-redis-prod"
check_service "kb-opensearch-prod"
check_service "kb-app-prod"
check_service "kb-nginx-prod"

# 6. Run database migrations
echo -e "\n${YELLOW}🗄️ Running database migrations...${NC}"
docker exec kb-app-prod alembic upgrade head || echo "Migrations skipped"

# 7. Create OpenSearch indices
echo -e "\n${YELLOW}🔍 Creating OpenSearch indices...${NC}"
docker exec kb-app-prod python -m app.scripts.init_opensearch || echo "OpenSearch init skipped"

# 8. Display access information
echo -e "\n${GREEN}✅ Deployment Complete!${NC}"
echo "=========================================="
echo -e "${GREEN}Application URL:${NC} http://localhost"
echo -e "${GREEN}API Documentation:${NC} http://localhost:8000/docs"
echo -e "${GREEN}Health Check:${NC} http://localhost:8000/health"
echo ""
echo -e "${YELLOW}📊 View logs:${NC}"
echo "  docker-compose -f docker-compose.prod.yml logs -f app"
echo ""
echo -e "${YELLOW}🛑 Stop services:${NC}"
echo "  docker-compose -f docker-compose.prod.yml down"
echo ""