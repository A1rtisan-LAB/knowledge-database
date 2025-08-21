# Test Environment Setup Guide

This guide provides instructions for setting up and running tests in the Knowledge Database project. We offer two testing approaches: Docker-based (recommended) and SQLite-based (fallback).

## Prerequisites

### For Docker-based Testing (Recommended)
- Docker Desktop installed and running
- Docker Compose v2.0+
- Python 3.11+
- 4GB+ available RAM

### For SQLite-based Testing (Alternative)
- Python 3.11+
- pip package manager
- 2GB+ available RAM

## Quick Start

### Option 1: Docker-based Testing (Full Integration)

```bash
# Start test services
./scripts/test-env.sh start

# Run all tests
./scripts/test-env.sh test

# Run specific test
./scripts/test-env.sh test tests/test_auth.py

# Check service status
./scripts/test-env.sh status

# Stop services
./scripts/test-env.sh stop

# Clean up everything
./scripts/test-env.sh clean
```

### Option 2: SQLite-based Testing (No Docker Required)

```bash
# Initial setup
./scripts/test-sqlite.sh setup

# Run all tests
./scripts/test-sqlite.sh test

# Run tests with coverage
./scripts/test-sqlite.sh test --coverage

# Run specific test
./scripts/test-sqlite.sh run tests/test_auth.py

# Clean up
./scripts/test-sqlite.sh clean
```

## Docker Test Environment

### Services Configuration

The Docker test environment includes:

1. **PostgreSQL 16** (Port 5433)
   - Database: `knowledge_test`
   - User: `testuser`
   - Password: `testpass`
   - Supports asyncpg driver

2. **OpenSearch 2.11.0** (Port 9201)
   - Single-node cluster
   - Security disabled for testing
   - Memory: 256MB

3. **Redis 7** (Port 6380)
   - In-memory only (no persistence)
   - Memory limit: 100MB

### File Structure

```
docker-compose.test.yml    # Test-specific Docker configuration
Dockerfile.test           # Test container definition
.env.test                # Test environment variables
tests/fixtures/          # Test data and SQL scripts
  └── init_test.sql     # Database initialization
```

### Running Tests in Docker

```bash
# Start services and run tests in one command
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Or use the helper script
./scripts/test-env.sh test --docker

# View logs
docker compose -f docker-compose.test.yml logs -f

# Access services directly
psql postgresql://testuser:testpass@localhost:5433/knowledge_test
curl http://localhost:9201/_cluster/health
redis-cli -p 6380
```

## SQLite Test Environment

### Features

The SQLite test environment provides:

- **SQLite in-memory database** - Fast, no persistence
- **Mocked OpenSearch** - Simulated search operations
- **Mocked Redis** - Simulated caching
- **Mocked Embedding Service** - Simulated vector operations

### Configuration

Uses `tests/conftest_sqlite.py` for test fixtures and mocks.

### Limitations

- No real full-text search capabilities
- No actual vector similarity search
- No distributed caching
- No real async database operations
- Simplified transaction handling

### When to Use SQLite Tests

Use SQLite testing when:
- Docker is not available
- Running quick unit tests
- Testing business logic
- CI/CD environments without Docker
- Local development on resource-constrained machines

## Environment Variables

### Test Environment (.env.test)

```env
# Security
SECRET_KEY=test-secret-key-for-testing-only
JWT_ALGORITHM=HS256
JWT_EXPIRATION_DELTA=3600

# Database (Docker)
DATABASE_URL=postgresql+asyncpg://testuser:testpass@localhost:5433/knowledge_test

# Database (SQLite)
# DATABASE_URL=sqlite+aiosqlite:///:memory:

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9201

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380

# Application
ENVIRONMENT=test
TESTING=true
```

## Test Organization

```
tests/
├── conftest.py          # Main test configuration
├── conftest_sqlite.py   # SQLite-specific configuration
├── unit/               # Unit tests (use SQLite)
│   ├── test_auth.py
│   ├── test_models.py
│   └── test_services.py
├── integration/        # Integration tests (use Docker)
│   └── test_api_endpoints.py
├── e2e/               # End-to-end tests (use Docker)
│   └── test_user_workflows.py
├── performance/       # Performance tests (use Docker)
│   └── test_load_performance.py
└── fixtures/          # Test data and SQL scripts
    └── init_test.sql
```

## Test Markers

```python
# Mark tests that require Docker services
@pytest.mark.integration
def test_opensearch_indexing():
    pass

# Mark slow tests
@pytest.mark.slow
def test_large_dataset():
    pass

# Mark tests that can run with SQLite
@pytest.mark.unit
def test_password_hashing():
    pass
```

Run specific test categories:

```bash
# Run only unit tests (SQLite-compatible)
pytest -m unit

# Run integration tests (requires Docker)
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

## Coverage Reports

### Generate Coverage

```bash
# Docker environment
./scripts/test-env.sh test --coverage

# SQLite environment
./scripts/test-sqlite.sh test --coverage
```

### View Coverage

- **HTML Report**: Open `htmlcov/index.html` in browser
- **Terminal Report**: Displayed after test run
- **XML Report**: `coverage.xml` for CI/CD integration

### Coverage Goals

- Overall: 80%+
- Core modules: 90%+
- API endpoints: 85%+
- Services: 75%+

## Troubleshooting

### Docker Issues

```bash
# Check Docker status
docker info

# View container logs
docker compose -f docker-compose.test.yml logs

# Reset everything
docker compose -f docker-compose.test.yml down -v
./scripts/test-env.sh clean

# Rebuild containers
docker compose -f docker-compose.test.yml build --no-cache
```

### SQLite Issues

```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete

# Reinstall dependencies
rm -rf venv/
./scripts/test-sqlite.sh setup

# Check Python version
python3 --version  # Should be 3.11+
```

### Common Problems

1. **Port conflicts**: Change ports in docker-compose.test.yml
2. **Memory issues**: Reduce service memory limits
3. **Permission errors**: Check file ownership and Docker permissions
4. **Import errors**: Verify PYTHONPATH and virtual environment
5. **Database errors**: Check connection strings in .env.test

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test-sqlite:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          pip install aiosqlite
      - run: pytest tests/unit/ --cov=app

  test-docker:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
    steps:
      - uses: actions/checkout@v2
      - run: docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Use Fixtures**: Leverage pytest fixtures for setup/teardown
3. **Mock External Services**: Use mocks for third-party APIs
4. **Test Data**: Use factories or fixtures, not production data
5. **Async Testing**: Use pytest-asyncio for async code
6. **Performance**: Keep tests fast (< 1 second per unit test)
7. **Documentation**: Document complex test scenarios
8. **Cleanup**: Always clean up resources after tests

## Performance Testing

For load and stress testing:

```bash
# Start services
./scripts/test-env.sh start

# Run performance tests
pytest tests/performance/ -v

# Generate load with locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

## Security Testing

```bash
# Run security-focused tests
pytest tests/security/ -v

# Check for vulnerabilities
pip install safety
safety check

# Static analysis
pip install bandit
bandit -r app/
```

## Maintenance

### Update Dependencies

```bash
# Update test requirements
pip install --upgrade -r requirements-test.txt

# Update Docker images
docker compose -f docker-compose.test.yml pull
```

### Clean Up Resources

```bash
# Remove all test artifacts
./scripts/test-env.sh clean
./scripts/test-sqlite.sh clean

# Remove Docker volumes
docker volume prune -f

# Remove unused Docker resources
docker system prune -af
```

## Support

For issues or questions:
1. Check this documentation
2. Review test logs
3. Check service health status
4. Verify environment variables
5. Ensure all dependencies are installed

Remember: Docker-based tests provide the most accurate testing environment, while SQLite-based tests offer a lightweight alternative for rapid development and CI/CD scenarios without Docker support.