# Makefile for Knowledge Database Testing

.PHONY: help install test test-docker test-sqlite coverage clean docker-up docker-down docker-clean

# Default target
help:
	@echo "Knowledge Database Test Environment"
	@echo ""
	@echo "Available targets:"
	@echo "  install        - Install all dependencies"
	@echo "  test          - Run tests (auto-detect Docker or SQLite)"
	@echo "  test-docker   - Run tests with Docker services"
	@echo "  test-sqlite   - Run tests with SQLite (no Docker)"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  coverage      - Run tests with coverage report"
	@echo "  clean         - Clean all test artifacts"
	@echo "  docker-up     - Start Docker test services"
	@echo "  docker-down   - Stop Docker test services"
	@echo "  docker-clean  - Clean Docker test environment"
	@echo "  format        - Format code with black and isort"
	@echo "  lint          - Run linting checks"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
	@pip install -r requirements-test.txt
	@echo "Dependencies installed successfully"

# Auto-detect and run appropriate test environment
test:
	@if docker info > /dev/null 2>&1; then \
		echo "Docker detected, running Docker-based tests..."; \
		./scripts/test-env.sh test; \
	else \
		echo "Docker not available, running SQLite-based tests..."; \
		./scripts/test-sqlite.sh test; \
	fi

# Run tests with Docker
test-docker:
	@echo "Running tests with Docker services..."
	@./scripts/test-env.sh start
	@./scripts/test-env.sh test
	@./scripts/test-env.sh stop

# Run tests with SQLite
test-sqlite:
	@echo "Running tests with SQLite backend..."
	@./scripts/test-sqlite.sh test

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	@if [ -d "venv" ]; then \
		. venv/bin/activate; \
	fi; \
	TESTING=true DATABASE_URL="sqlite+aiosqlite:///:memory:" \
	pytest tests/unit/ -v --tb=short

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	@if docker info > /dev/null 2>&1; then \
		./scripts/test-env.sh start; \
		./scripts/test-env.sh test tests/integration/; \
		./scripts/test-env.sh stop; \
	else \
		echo "Integration tests require Docker"; \
		exit 1; \
	fi

# Run tests with coverage
coverage:
	@echo "Running tests with coverage..."
	@if docker info > /dev/null 2>&1; then \
		./scripts/test-env.sh test --coverage; \
	else \
		./scripts/test-sqlite.sh test --coverage; \
	fi
	@echo "Coverage report: htmlcov/index.html"

# Clean test artifacts
clean:
	@echo "Cleaning test artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -f .coverage coverage.xml
	@rm -rf htmlcov/
	@echo "Clean complete"

# Docker operations
docker-up:
	@echo "Starting Docker test services..."
	@docker compose -f docker-compose.test.yml up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@docker compose -f docker-compose.test.yml ps

docker-down:
	@echo "Stopping Docker test services..."
	@docker compose -f docker-compose.test.yml down

docker-clean:
	@echo "Cleaning Docker test environment..."
	@docker compose -f docker-compose.test.yml down -v
	@docker volume ls | grep knowledge-test | awk '{print $$2}' | xargs -r docker volume rm 2>/dev/null || true
	@echo "Docker cleanup complete"

# Code formatting
format:
	@echo "Formatting code..."
	@black app/ tests/ --line-length 100
	@isort app/ tests/ --profile black --line-length 100
	@echo "Code formatted"

# Linting
lint:
	@echo "Running linting checks..."
	@flake8 app/ tests/ --max-line-length 100 --ignore E203,W503
	@mypy app/ --ignore-missing-imports
	@echo "Linting complete"

# Quick test for CI/CD
test-ci:
	@echo "Running CI tests..."
	@pytest tests/unit/ -v --tb=short --cov=app --cov-report=xml

# Development server with test database
dev-test:
	@echo "Starting development server with test database..."
	@if docker info > /dev/null 2>&1; then \
		./scripts/test-env.sh start; \
		export DATABASE_URL="postgresql+asyncpg://testuser:testpass@localhost:5433/knowledge_test"; \
		export OPENSEARCH_HOST="localhost"; \
		export OPENSEARCH_PORT="9201"; \
		export REDIS_HOST="localhost"; \
		export REDIS_PORT="6380"; \
		uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; \
	else \
		echo "Development server requires Docker services"; \
		exit 1; \
	fi

# Watch tests (requires pytest-watch)
watch:
	@echo "Watching for test changes..."
	@pip install pytest-watch
	@ptw tests/ -- -v --tb=short

# Performance testing
test-performance:
	@echo "Running performance tests..."
	@if docker info > /dev/null 2>&1; then \
		./scripts/test-env.sh start; \
		pytest tests/performance/ -v; \
		./scripts/test-env.sh stop; \
	else \
		echo "Performance tests require Docker"; \
		exit 1; \
	fi

# Security testing
test-security:
	@echo "Running security tests..."
	@pip install safety bandit
	@safety check
	@bandit -r app/ -f json -o security-report.json
	@echo "Security report saved to security-report.json"

# Full test suite
test-all: lint test-unit test-integration test-performance coverage
	@echo "All tests completed"

# Docker compose shortcuts
up: docker-up
down: docker-down

# Test shortcuts
t: test
tu: test-unit
ti: test-integration
tc: coverage

.DEFAULT_GOAL := help