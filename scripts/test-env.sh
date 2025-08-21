#!/bin/bash

# Test Environment Management Script
# Usage: ./scripts/test-env.sh [start|stop|restart|status|test|clean]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.test.yml"
ENV_FILE=".env.test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check Docker installation
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    
    log_info "Docker is installed and running."
}

# Start test environment
start_services() {
    log_info "Starting test environment services..."
    
    cd "$PROJECT_ROOT"
    
    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    fi
    
    # Start services
    docker compose -f "$COMPOSE_FILE" up -d postgres-test opensearch-test redis-test
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            local healthy_count=$(docker compose -f "$COMPOSE_FILE" ps | grep -c "healthy" || true)
            if [ "$healthy_count" -ge 3 ]; then
                log_info "All services are healthy!"
                break
            fi
        fi
        
        attempt=$((attempt + 1))
        log_info "Waiting for services... (attempt $attempt/$max_attempts)"
        sleep 5
    done
    
    if [ $attempt -eq $max_attempts ]; then
        log_error "Services failed to become healthy in time."
        docker compose -f "$COMPOSE_FILE" ps
        exit 1
    fi
    
    # Show service status
    docker compose -f "$COMPOSE_FILE" ps
}

# Stop test environment
stop_services() {
    log_info "Stopping test environment services..."
    
    cd "$PROJECT_ROOT"
    docker compose -f "$COMPOSE_FILE" down
    
    log_info "Services stopped."
}

# Restart test environment
restart_services() {
    stop_services
    start_services
}

# Check service status
check_status() {
    log_info "Checking test environment status..."
    
    cd "$PROJECT_ROOT"
    
    echo ""
    echo "Service Status:"
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "Service Health:"
    
    # Check PostgreSQL
    if docker compose -f "$COMPOSE_FILE" exec -T postgres-test pg_isready -U testuser -d knowledge_test &> /dev/null; then
        log_info "PostgreSQL: Healthy"
    else
        log_error "PostgreSQL: Unhealthy or not running"
    fi
    
    # Check OpenSearch
    if curl -sf http://localhost:9201/_cluster/health &> /dev/null; then
        log_info "OpenSearch: Healthy"
    else
        log_error "OpenSearch: Unhealthy or not running"
    fi
    
    # Check Redis
    if docker compose -f "$COMPOSE_FILE" exec -T redis-test redis-cli ping &> /dev/null; then
        log_info "Redis: Healthy"
    else
        log_error "Redis: Unhealthy or not running"
    fi
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Check if services are running
    if ! docker compose -f "$COMPOSE_FILE" ps | grep -q "postgres-test.*running"; then
        log_warning "Services are not running. Starting them first..."
        start_services
    fi
    
    # Run tests in Docker
    if [ "$1" == "--docker" ]; then
        log_info "Running tests in Docker container..."
        docker compose -f "$COMPOSE_FILE" run --rm test-runner
    else
        # Run tests locally
        log_info "Running tests locally..."
        
        # Load test environment
        if [ -f "$ENV_FILE" ]; then
            export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
        fi
        
        # Update environment for local testing
        export DATABASE_URL="postgresql+asyncpg://testuser:testpass@localhost:5433/knowledge_test"
        export OPENSEARCH_HOST="localhost"
        export OPENSEARCH_PORT="9201"
        export REDIS_HOST="localhost"
        export REDIS_PORT="6380"
        export TESTING="true"
        
        # Run pytest
        if [ -n "$2" ]; then
            # Run specific test
            pytest "$2" -v --tb=short --color=yes
        else
            # Run all tests
            pytest tests/ -v --tb=short --color=yes --cov=app --cov-report=html --cov-report=term
        fi
    fi
}

# Clean up everything
clean_up() {
    log_info "Cleaning up test environment..."
    
    cd "$PROJECT_ROOT"
    
    # Stop and remove containers
    docker compose -f "$COMPOSE_FILE" down -v
    
    # Remove test database volumes
    docker volume ls | grep knowledge-test | awk '{print $2}' | xargs -r docker volume rm
    
    # Clean pytest cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    
    log_info "Cleanup complete."
}

# Main script
main() {
    case "$1" in
        start)
            check_docker
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            check_docker
            restart_services
            ;;
        status)
            check_status
            ;;
        test)
            check_docker
            run_tests "$2" "$3"
            ;;
        clean)
            clean_up
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|test|clean}"
            echo ""
            echo "Commands:"
            echo "  start    - Start test environment services"
            echo "  stop     - Stop test environment services"
            echo "  restart  - Restart test environment services"
            echo "  status   - Check service status"
            echo "  test     - Run tests (add --docker to run in container)"
            echo "  clean    - Clean up everything (containers, volumes, cache)"
            echo ""
            echo "Examples:"
            echo "  $0 start                    # Start services"
            echo "  $0 test                     # Run all tests locally"
            echo "  $0 test --docker            # Run tests in Docker"
            echo "  $0 test tests/test_auth.py # Run specific test"
            exit 1
            ;;
    esac
}

main "$@"