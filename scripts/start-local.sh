#!/bin/bash

# Knowledge Database Local Start Script
# This script automates the setup and startup process for local development

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Knowledge Database Local Setup${NC}"

# 1. Check Docker daemon
echo -e "\n${YELLOW}Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    
    # Try to start Docker Desktop on macOS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${YELLOW}Attempting to start Docker Desktop...${NC}"
        open -a Docker
        echo "Waiting for Docker to start (30 seconds)..."
        sleep 30
        
        if ! docker info > /dev/null 2>&1; then
            echo -e "${RED}Docker still not running. Please start it manually.${NC}"
            exit 1
        fi
    else
        exit 1
    fi
fi
echo -e "${GREEN}✅ Docker is running${NC}"

# 2. Clean up any existing processes
echo -e "\n${YELLOW}Cleaning up existing processes...${NC}"
pkill -f uvicorn 2>/dev/null || true
echo -e "${GREEN}✅ Cleanup complete${NC}"

# 3. Check/create environment file
echo -e "\n${YELLOW}Checking environment configuration...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Created .env file from .env.example${NC}"
        echo -e "${YELLOW}   Please review and update the settings in .env${NC}"
    else
        echo -e "${RED}❌ No .env or .env.example file found!${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Environment file exists${NC}"
fi

# 4. Check for service selection flags
MINIMAL_MODE=false
BACKGROUND_MODE=false

for arg in "$@"; do
    case $arg in
        --minimal)
            MINIMAL_MODE=true
            echo -e "${YELLOW}🔧 Running in minimal mode (PostgreSQL and Redis only)${NC}"
            ;;
        --background|-b)
            BACKGROUND_MODE=true
            echo -e "${YELLOW}🔧 Running FastAPI in background mode${NC}"
            ;;
        --help|-h)
            echo -e "${GREEN}Knowledge Database Local Start Script${NC}"
            echo -e "Usage: $0 [OPTIONS]"
            echo -e "Options:"
            echo -e "  --minimal      Start only PostgreSQL and Redis (skip OpenSearch)"
            echo -e "  --background   Run FastAPI in background (returns to shell)"
            echo -e "  --help         Show this help message"
            exit 0
            ;;
    esac
done

# 5. Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
if [ "$MINIMAL_MODE" = true ]; then
    docker-compose up -d postgres redis
    SERVICES_TO_CHECK=("postgres" "redis")
else
    docker-compose up -d postgres redis opensearch opensearch-dashboards
    SERVICES_TO_CHECK=("postgres" "redis" "opensearch" "opensearch-dashboards")
fi

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec knowledge-postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Wait for Redis to be ready
echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
for i in {1..30}; do
    if docker exec knowledge-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done

# Wait for OpenSearch to be ready (if not in minimal mode)
if [ "$MINIMAL_MODE" = false ]; then
    echo -e "${YELLOW}Waiting for OpenSearch to be ready (this may take a minute)...${NC}"
    for i in {1..60}; do
        if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ OpenSearch is ready${NC}"
            break
        fi
        if [ $i -eq 60 ]; then
            echo -e "${YELLOW}⚠️  OpenSearch is taking longer than expected to start${NC}"
            echo -e "${YELLOW}   You can check its status later at http://localhost:9200${NC}"
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for OpenSearch Dashboards to be ready
    echo -e "${YELLOW}Waiting for OpenSearch Dashboards to be ready...${NC}"
    for i in {1..60}; do
        if curl -s http://localhost:5601/api/status > /dev/null 2>&1; then
            echo -e "${GREEN}✅ OpenSearch Dashboards is ready${NC}"
            break
        fi
        if [ $i -eq 60 ]; then
            echo -e "${YELLOW}⚠️  OpenSearch Dashboards is taking longer than expected${NC}"
            echo -e "${YELLOW}   You can check its status later at http://localhost:5601${NC}"
        fi
        echo -n "."
        sleep 2
    done
fi

# 6. Initialize PostgreSQL extensions
echo -e "\n${YELLOW}Setting up PostgreSQL extensions...${NC}"
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || {
    echo -e "${YELLOW}Creating database and extensions...${NC}"
    docker exec knowledge-postgres psql -U postgres -c "CREATE DATABASE knowledge_db;" 2>/dev/null || true
    docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
    docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
}
echo -e "${GREEN}✅ PostgreSQL extensions configured${NC}"

# 7. Setup Python virtual environment
echo -e "\n${YELLOW}Setting up Python environment...${NC}"
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# 8. Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
if [ -f "requirements-core.txt" ]; then
    pip install -q --upgrade pip
    pip install -q -r requirements-core.txt
    echo -e "${GREEN}✅ Core dependencies installed${NC}"
else
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
fi

# 9. Run database migrations (skip if alembic.ini doesn't exist)
echo -e "\n${YELLOW}Checking database migrations...${NC}"
if [ -f "alembic.ini" ]; then
    echo -e "${YELLOW}Running database migrations...${NC}"
    alembic upgrade head 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Migration failed, but continuing...${NC}"
    }
    echo -e "${GREEN}✅ Database migrations complete${NC}"
else
    echo -e "${YELLOW}ℹ️  No alembic.ini found, skipping migrations${NC}"
fi

# 10. Display running services status
echo -e "\n${GREEN}📊 Running Services Status:${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "knowledge-|NAMES"
echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"

# 11. Start the application
echo -e "\n${GREEN}🎉 Starting FastAPI application...${NC}"
echo -e "\n${YELLOW}🌐 Access Points:${NC}"
echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
echo -e "  📚 API Documentation:        ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  📖 ReDoc:                    ${GREEN}http://localhost:8000/redoc${NC}"
echo -e "  🔍 Health Check:             ${GREEN}http://localhost:8000/health${NC}"
echo -e "  🗄️  PostgreSQL:               ${GREEN}localhost:5432${NC}"
echo -e "  📦 Redis:                    ${GREEN}localhost:6379${NC}"
if [ "$MINIMAL_MODE" = false ]; then
    echo -e "  🔍 OpenSearch:               ${GREEN}http://localhost:9200${NC}"
    echo -e "  📊 OpenSearch Dashboards:    ${GREEN}http://localhost:5601${NC}"
fi
echo -e "${YELLOW}─────────────────────────────────────────────────${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ "$BACKGROUND_MODE" = true ]; then
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
    fi
    docker-compose down
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Start uvicorn
if [ "$BACKGROUND_MODE" = true ]; then
    echo -e "${YELLOW}Starting FastAPI in background...${NC}"
    nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
    UVICORN_PID=$!
    echo -e "${GREEN}✅ FastAPI started with PID: $UVICORN_PID${NC}"
    echo -e "\n${YELLOW}Services are running in background.${NC}"
    echo -e "${YELLOW}To stop all services, run: docker-compose down && pkill -f uvicorn${NC}"
    echo -e "${YELLOW}To view FastAPI logs, run: tail -f logs/uvicorn.log${NC}"
    echo -e "${YELLOW}To check service status, run: docker ps${NC}"
    # Don't set trap in background mode
else
    # Set trap to cleanup on script exit (only for foreground mode)
    trap cleanup EXIT INT TERM
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
fi